"""
noteAI データ収集スクリプト v3.0
2026年世界最高水準版

改善点:
- 50+カテゴリのキーワード（3→50+）
- ユーザー収集目標 200+ （26→200+）
- Power Score 多次元評価
- Evol-Instruct対応データ形式
- レジューム機能強化
- レート制限対応
"""

import csv
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# ============================================================
# 設定
# ============================================================

# 50+カテゴリのキーワード（世界水準: 多様性確保）
SEARCH_KEYWORDS = {
    # ライフスタイル・生活 (10)
    "lifestyle": [
        "一人暮らし", "ミニマリスト", "丁寧な暮らし", "時短", "整理収納",
        "朝活", "夜活", "習慣化", "ルーティン", "シンプルライフ"
    ],
    # キャリア・仕事 (10)
    "career": [
        "副業", "転職", "フリーランス", "リモートワーク", "起業",
        "キャリアチェンジ", "会社員", "独立", "スキルアップ", "年収"
    ],
    # クリエイティブ (10)
    "creative": [
        "文章術", "ライティング", "note初心者", "アウトプット", "創作",
        "小説", "エッセイ", "ポートフォリオ", "発信", "ブログ"
    ],
    # 自己啓発・学び (10)
    "growth": [
        "読書", "勉強法", "英語学習", "資格", "自己投資",
        "継続", "目標達成", "モチベーション", "マインドセット", "成長"
    ],
    # お金・投資 (8)
    "money": [
        "節約", "貯金", "投資", "NISA", "家計簿",
        "お金の話", "資産形成", "経済的自由"
    ],
    # テクノロジー (8)
    "tech": [
        "AI", "ChatGPT", "プログラミング", "Python", "エンジニア",
        "IT転職", "ノーコード", "生成AI"
    ],
    # 健康・メンタル (8)
    "health": [
        "ダイエット", "筋トレ", "メンタルヘルス", "うつ病", "HSP",
        "睡眠", "ストレス", "自律神経"
    ],
    # 人間関係 (6)
    "relationship": [
        "人間関係", "コミュニケーション", "婚活", "恋愛", "夫婦", "育児"
    ],
}

# すべてのキーワードをフラット化
ALL_KEYWORDS = []
for category, keywords in SEARCH_KEYWORDS.items():
    for kw in keywords:
        ALL_KEYWORDS.append((category, kw))

# APIエンドポイント
BASE_URL = "https://note.com/api"

# 収集設定
CONFIG = {
    "max_users": 300,           # 目標ユーザー数（26→300）
    "max_followers": 2000,      # フォロワー上限（1000→2000）
    "min_likes_per_article": 30,  # 記事あたり最低いいね数
    "power_score_threshold": 0.8,  # Power Score閾値
    "request_delay": 1.5,       # リクエスト間隔（秒）
    "max_retries": 3,           # リトライ回数
    "articles_per_user": 50,    # ユーザーあたり最大記事数
}

# ファイルパス
DATA_DIR = Path("data")
PROGRESS_FILE = DATA_DIR / "collection_progress_v3.json"
RAW_DATA_FILE = DATA_DIR / "raw_notes_v3.jsonl"
USERS_FILE = DATA_DIR / "collected_users_v3.json"

# HTTPヘッダー（403対策）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://note.com/",
    "Origin": "https://note.com",
}

# ============================================================
# データクラス
# ============================================================

@dataclass
class NoteData:
    """記事データ"""
    note_id: str
    title: str
    body_preview: str
    user_id: str
    user_name: str
    user_nickname: str
    follower_count: int
    like_count: int
    comment_count: int
    created_at: str
    category: str
    keyword: str

    # 多次元Power Score
    power_score: float = 0.0
    engagement_rate: float = 0.0
    virality_score: float = 0.0

    def calculate_scores(self):
        """多次元スコアを計算"""
        # 基本Power Score（フォロワー比）
        if self.follower_count > 0:
            self.power_score = self.like_count / self.follower_count
        else:
            self.power_score = self.like_count  # フォロワー0の場合はいいね数をそのまま

        # Engagement Rate（総エンゲージメント÷フォロワー）
        total_engagement = self.like_count + (self.comment_count * 3)  # コメントは3倍重み
        if self.follower_count > 0:
            self.engagement_rate = total_engagement / self.follower_count
        else:
            self.engagement_rate = total_engagement

        # Virality Score（指数的拡散の指標）
        # フォロワー少×高いいね = 高スコア
        if self.follower_count > 0:
            self.virality_score = (self.like_count ** 1.5) / (self.follower_count ** 0.5)
        else:
            self.virality_score = self.like_count ** 1.5

# ============================================================
# API関数
# ============================================================

def safe_request(url: str, retries: int = CONFIG["max_retries"]) -> Optional[Dict]:
    """安全なAPIリクエスト（リトライ付き）"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # レート制限
                wait_time = 60 * (attempt + 1)
                print(f"  ⚠️ レート制限。{wait_time}秒待機...")
                time.sleep(wait_time)
            elif response.status_code == 404:
                return None
            elif response.status_code == 403:
                # 403の場合は少し待って再試行
                wait_time = 10 * (attempt + 1)
                print(f"  ⚠️ HTTP 403。{wait_time}秒待機後リトライ...")
                time.sleep(wait_time)
            else:
                print(f"  ⚠️ HTTP {response.status_code}")
                time.sleep(5)
        except Exception as e:
            print(f"  ⚠️ リクエストエラー: {e}")
            time.sleep(5)
    return None

def get_user_info(user_id: str) -> Optional[Dict]:
    """ユーザー情報を取得"""
    url = f"{BASE_URL}/v2/creators/{user_id}"
    data = safe_request(url)
    if data and "data" in data:
        return data["data"]
    return None

def get_user_notes(user_id: str, page: int = 1) -> List[Dict]:
    """ユーザーの記事一覧を取得"""
    url = f"{BASE_URL}/v2/creators/{user_id}/contents?kind=note&page={page}"
    data = safe_request(url)
    if data and "data" in data and "contents" in data["data"]:
        return data["data"]["contents"]
    return []

def search_notes(keyword: str, page: int = 1) -> List[Dict]:
    """キーワードで記事を検索"""
    # v3 API: size=20, note_cursor でページング
    url = f"{BASE_URL}/v3/searches?q={keyword}&size=20"
    data = safe_request(url)
    if data and "data" in data:
        notes_data = data["data"].get("notes", {})
        if isinstance(notes_data, dict) and "contents" in notes_data:
            return notes_data["contents"]
    return []

# ============================================================
# 収集ロジック
# ============================================================

class DataCollector:
    def __init__(self):
        self.collected_users: set = set()
        self.collected_notes: set = set()
        self.progress: Dict = {
            "completed_keywords": [],
            "current_keyword_index": 0,
            "total_notes": 0,
            "total_users": 0,
            "started_at": None,
            "last_updated": None,
        }
        self.load_progress()

    def load_progress(self):
        """進捗をロード"""
        DATA_DIR.mkdir(exist_ok=True)

        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                self.progress = json.load(f)
            print(f"📂 進捗をロード: {self.progress['total_notes']}記事, {self.progress['total_users']}ユーザー")

        if USERS_FILE.exists():
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                self.collected_users = set(json.load(f))

        if RAW_DATA_FILE.exists():
            with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        note = json.loads(line)
                        self.collected_notes.add(note.get("note_id", ""))
                    except:
                        pass

    def save_progress(self):
        """進捗を保存"""
        self.progress["last_updated"] = datetime.now().isoformat()
        self.progress["total_users"] = len(self.collected_users)

        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)

        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(self.collected_users), f, ensure_ascii=False)

    def save_note(self, note_data: NoteData):
        """記事データを保存"""
        with open(RAW_DATA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(note_data), ensure_ascii=False) + "\n")
        self.progress["total_notes"] += 1
        self.collected_notes.add(note_data.note_id)

    def process_user(self, urlname: str, category: str, keyword: str) -> int:
        """ユーザーの記事を処理（urlnameを使用）"""
        if urlname in self.collected_users:
            return 0

        # ユーザー情報取得
        user_info = get_user_info(urlname)
        if not user_info:
            return 0

        follower_count = user_info.get("followerCount", 0)

        # フォロワー数フィルタ
        if follower_count > CONFIG["max_followers"]:
            return 0

        nickname = user_info.get("nickname", "")

        print(f"  👤 {nickname} (@{urlname}) - {follower_count}フォロワー")

        # 記事を収集
        notes_collected = 0
        page = 1

        while notes_collected < CONFIG["articles_per_user"]:
            time.sleep(CONFIG["request_delay"])
            notes = get_user_notes(urlname, page)

            if not notes:
                break

            for note in notes:
                note_id = str(note.get("id", ""))
                if note_id in self.collected_notes:
                    continue

                like_count = note.get("likeCount", 0)

                # いいね数フィルタ
                if like_count < CONFIG["min_likes_per_article"]:
                    continue

                # NoteDataを作成
                note_data = NoteData(
                    note_id=note_id,
                    title=note.get("name", ""),
                    body_preview=note.get("body", "")[:500] if note.get("body") else "",
                    user_id=urlname,
                    user_name=urlname,
                    user_nickname=nickname,
                    follower_count=follower_count,
                    like_count=like_count,
                    comment_count=note.get("commentCount", 0),
                    created_at=note.get("publishAt", ""),
                    category=category,
                    keyword=keyword,
                )
                note_data.calculate_scores()

                # Power Score フィルタ
                if note_data.power_score >= CONFIG["power_score_threshold"]:
                    self.save_note(note_data)
                    notes_collected += 1
                    print(f"    ✅ {note_data.title[:30]}... (PS={note_data.power_score:.2f})")

            page += 1
            if page > 5:  # 最大5ページ
                break

        self.collected_users.add(urlname)
        return notes_collected

    def collect_from_keyword(self, category: str, keyword: str):
        """キーワードから収集"""
        print(f"\n🔍 [{category}] '{keyword}' を検索中...")

        users_found = {}  # urlname -> user_data

        for page in range(5):  # 最大5ページ
            time.sleep(CONFIG["request_delay"])
            notes = search_notes(keyword, page)

            if not notes:
                break

            for note in notes:
                user_data = note.get("user", {})
                urlname = user_data.get("urlname", "")
                if urlname and urlname not in users_found:
                    users_found[urlname] = user_data

        print(f"  📊 {len(users_found)}人のユーザーを発見")

        # 各ユーザーを処理（urlnameを使用）
        for urlname in users_found:
            if len(self.collected_users) >= CONFIG["max_users"]:
                print(f"\n🎯 目標ユーザー数 ({CONFIG['max_users']}) に到達!")
                return

            time.sleep(CONFIG["request_delay"])
            self.process_user(urlname, category, keyword)

        self.progress["completed_keywords"].append(f"{category}:{keyword}")
        self.save_progress()

    def run(self):
        """メイン収集ループ"""
        if not self.progress["started_at"]:
            self.progress["started_at"] = datetime.now().isoformat()

        print("=" * 60)
        print("🚀 noteAI データ収集 v3.0 開始")
        print(f"📊 目標: {CONFIG['max_users']}ユーザー, {len(ALL_KEYWORDS)}キーワード")
        print("=" * 60)

        start_index = self.progress["current_keyword_index"]

        for i, (category, keyword) in enumerate(ALL_KEYWORDS[start_index:], start=start_index):
            # 進捗表示
            print(f"\n[{i+1}/{len(ALL_KEYWORDS)}] 処理中...")

            self.progress["current_keyword_index"] = i
            self.collect_from_keyword(category, keyword)

            # 定期保存
            if i % 5 == 0:
                self.save_progress()

            # 目標達成チェック
            if len(self.collected_users) >= CONFIG["max_users"]:
                break

        # 最終保存
        self.save_progress()

        print("\n" + "=" * 60)
        print("✅ 収集完了!")
        print(f"📊 合計: {self.progress['total_notes']}記事, {len(self.collected_users)}ユーザー")
        print("=" * 60)

# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":
    collector = DataCollector()
    collector.run()
