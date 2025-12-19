"""
note特化型AI開発プロジェクト - 大規模データ収集スクリプト（v2）

【改善点】
- 検索キーワードを大幅拡張（50+カテゴリ）
- 有料記事のみを優先収集
- より多くのデータを網羅的に収集
- 進捗表示の改善
- 中断・再開機能

【収集ターゲット】
- フォロワー: 10〜1000人（実力勝負の層）
- 有料記事: 優先収集（売れるタイトルの学習に最適）
- Power Score: スキ数÷フォロワー数（純粋なタイトル力の指標）
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ==========================================
# 設定
# ==========================================

# 検索キーワード（網羅的に設定）
SEARCH_KEYWORDS = [
    # マネー・副業系
    "副業",
    "稼ぐ",
    "収益",
    "月収",
    "年収",
    "不労所得",
    "投資",
    "株",
    "FX",
    "仮想通貨",
    "ビットコイン",
    "NISA",
    "iDeCo",
    "ポイ活",
    "せどり",
    "転売",
    "アフィリエイト",
    "ブログ収益",
    "note収益",
    "マネタイズ",
    # ビジネス・キャリア系
    "転職",
    "起業",
    "独立",
    "フリーランス",
    "リモートワーク",
    "在宅ワーク",
    "営業",
    "マーケティング",
    "コンサル",
    "経営",
    "MBA",
    "キャリア",
    # クリエイター系
    "ブログ",
    "ライティング",
    "Webライター",
    "コピーライティング",
    "デザイン",
    "イラスト",
    "写真",
    "動画編集",
    "YouTube",
    "TikTok",
    "SNS運用",
    "Twitter",
    "Instagram",
    "Threads",
    # AI・テクノロジー系
    "AI",
    "ChatGPT",
    "Claude",
    "Gemini",
    "プロンプト",
    "生成AI",
    "プログラミング",
    "Python",
    "エンジニア",
    "Notion",
    "自動化",
    # 自己啓発・ライフスタイル系
    "習慣",
    "朝活",
    "読書",
    "勉強法",
    "資格",
    "TOEIC",
    "英語学習",
    "ミニマリスト",
    "断捨離",
    "時間管理",
    "タスク管理",
    # 恋愛・人間関係系
    "恋愛",
    "婚活",
    "マッチングアプリ",
    "モテる",
    "コミュニケーション",
    "人間関係",
    "心理学",
    "メンタル",
    "自己肯定感",
    # 育児・家庭系
    "子育て",
    "育児",
    "ワーママ",
    "共働き",
    "教育",
    "中学受験",
    # 健康・美容系
    "ダイエット",
    "筋トレ",
    "美容",
    "スキンケア",
    "健康",
    # ニッチ系（有料記事が多い分野）
    "占い",
    "タロット",
    "スピリチュアル",
    "風水",
    "不動産投資",
    "物販",
    "せどり",
    "輸入",
    "コーチング",
    "カウンセリング",
    "セラピスト",
]

# フォロワー数の条件（インフルエンサー除外、実力勝負の層を狙う）
MIN_FOLLOWERS = 10
MAX_FOLLOWERS = 1000

# 1キーワードあたりの検索結果数（最大値）
SEARCH_SIZE = 100

# APIアクセス間隔（秒）- サーバー負荷軽減
SLEEP_TIME = 2.5

# 有料記事のみを収集するか
PAID_ONLY = True

# 最低スキ数（ノイズ除去）
MIN_LIKES = 5

# 共通ヘッダー
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# 進捗保存ファイル
PROGRESS_FILE = "collection_progress.json"
OUTPUT_FILE = "note_power_data.csv"


# ==========================================
# 進捗管理
# ==========================================


def load_progress() -> dict:
    """進捗データを読み込み"""
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_keywords": [], "discovered_users": [], "collected_users": []}


def save_progress(progress: dict):
    """進捗データを保存"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ==========================================
# API関数
# ==========================================


def get_user_info(user_id: str) -> Optional[dict]:
    """ユーザー情報を取得"""
    url = f"https://note.com/api/v2/creators/{user_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()["data"]
    except Exception:
        pass
    return None


def get_user_notes(user_id: str, max_pages: int = 20) -> list:
    """ユーザーの全記事を取得（ページネーション対応）"""
    all_notes = []
    page = 1

    while page <= max_pages:
        url = (
            f"https://note.com/api/v2/creators/{user_id}/contents?kind=note&page={page}"
        )
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                break

            data = r.json()["data"]
            notes = data.get("contents", [])

            if not notes:
                break

            all_notes.extend(notes)

            if data.get("isLastPage", True):
                break

            page += 1
            time.sleep(SLEEP_TIME)

        except Exception:
            break

    return all_notes


def search_notes(keyword: str, size: int = 100) -> list:
    """キーワードで記事を検索"""
    url = f"https://note.com/api/v3/searches?q={keyword}&size={size}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()["data"]
            notes_data = data.get("notes", {})
            if isinstance(notes_data, dict):
                return notes_data.get("contents", [])
    except Exception:
        pass
    return []


# ==========================================
# メイン収集ロジック
# ==========================================


def collect_data(resume: bool = True) -> pd.DataFrame:
    """完全なデータ収集フロー（中断・再開対応）"""

    start_time = datetime.now()

    print("=" * 70)
    print("【note特化型AI 大規模データ収集 v2】")
    print(f"開始時刻: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"検索キーワード数: {len(SEARCH_KEYWORDS)}")
    print(f"対象フォロワー数: {MIN_FOLLOWERS}〜{MAX_FOLLOWERS}")
    print(f"有料記事のみ: {'はい' if PAID_ONLY else 'いいえ'}")
    print("=" * 70)

    # 進捗読み込み
    if resume:
        progress = load_progress()
        print("\n📂 前回の進捗を読み込み:")
        print(
            f"   完了キーワード: {len(progress['completed_keywords'])}/{len(SEARCH_KEYWORDS)}"
        )
        print(f"   発見ユーザー: {len(progress['discovered_users'])}人")
        print(f"   収集済みユーザー: {len(progress['collected_users'])}人")
    else:
        progress = {
            "completed_keywords": [],
            "discovered_users": [],
            "collected_users": [],
        }

    discovered_users = set(progress["discovered_users"])
    collected_users = set(progress["collected_users"])

    # =====================
    # STEP 1: ユーザー発見
    # =====================
    print("\n" + "=" * 70)
    print("[STEP 1/3] キーワード検索でユーザーを発見中...")
    print("=" * 70)

    remaining_keywords = [
        kw for kw in SEARCH_KEYWORDS if kw not in progress["completed_keywords"]
    ]
    total_keywords = len(SEARCH_KEYWORDS)

    for i, keyword in enumerate(
        remaining_keywords, len(progress["completed_keywords"]) + 1
    ):
        print(f"\n  [{i}/{total_keywords}] 検索中: 「{keyword}」", end="", flush=True)

        notes = search_notes(keyword, SEARCH_SIZE)
        new_users = 0

        for note in notes:
            user = note.get("user", {})
            urlname = user.get("urlname")
            if urlname and urlname not in discovered_users:
                discovered_users.add(urlname)
                new_users += 1

        print(f" → {len(notes)}件取得, 新規{new_users}人発見")

        # 進捗保存
        progress["completed_keywords"].append(keyword)
        progress["discovered_users"] = list(discovered_users)
        save_progress(progress)

        time.sleep(SLEEP_TIME)

    print(f"\n✓ 合計発見ユーザー数: {len(discovered_users)}人")

    # =====================
    # STEP 2: フォロワー数確認
    # =====================
    print("\n" + "=" * 70)
    print("[STEP 2/3] フォロワー数を確認して対象ユーザーを絞り込み中...")
    print("=" * 70)

    # 未確認のユーザーのみ処理
    unchecked_users = [u for u in discovered_users if u not in collected_users]
    target_users = []

    print(f"\n  確認対象: {len(unchecked_users)}人")

    for i, user_id in enumerate(unchecked_users, 1):
        if i % 20 == 0 or i == len(unchecked_users):
            print(
                f"  進捗: {i}/{len(unchecked_users)} ({i * 100 // len(unchecked_users)}%)"
            )

        user_info = get_user_info(user_id)
        if user_info:
            followers = user_info.get("followerCount", 0)

            if MIN_FOLLOWERS <= followers <= MAX_FOLLOWERS:
                target_users.append(
                    {
                        "user_id": user_id,
                        "nickname": user_info.get("nickname", ""),
                        "followers": followers,
                        "note_count": user_info.get("noteCount", 0),
                    }
                )

        time.sleep(SLEEP_TIME)

    print(f"\n✓ 条件に合うユーザー: {len(target_users)}人")

    if not target_users:
        print("\n⚠️ 条件に合うユーザーが見つかりませんでした。")
        return pd.DataFrame()

    # =====================
    # STEP 3: 記事データ収集
    # =====================
    print("\n" + "=" * 70)
    print("[STEP 3/3] 記事データを収集中...")
    if PAID_ONLY:
        print("※ 有料記事のみを収集します")
    print("=" * 70)

    all_data = []
    paid_count = 0

    for i, user in enumerate(target_users, 1):
        user_id = user["user_id"]
        followers = user["followers"]
        nickname = user["nickname"]

        print(
            f"\n  [{i}/{len(target_users)}] @{user_id} ({nickname}) - {followers}フォロワー"
        )

        notes = get_user_notes(user_id)
        user_paid = 0

        for note in notes:
            price = note.get("price", 0) or 0  # Noneの場合も0に
            is_paid = price > 0  # price > 0 なら有料記事
            likes = note.get("likeCount", 0)

            # 有料記事のみモードの場合、無料記事はスキップ
            if PAID_ONLY and not is_paid:
                continue

            # 最低スキ数チェック
            if likes < MIN_LIKES:
                continue

            title = note.get("name", "")
            note_key = note.get("key", "")
            price = note.get("price", 0)

            # 実力スコア = スキ数 ÷ フォロワー数
            power_score = round(likes / followers, 4) if followers > 0 else 0

            all_data.append(
                {
                    "user_id": user_id,
                    "nickname": nickname,
                    "followers": followers,
                    "title": title,
                    "likes": likes,
                    "power_score": power_score,
                    "is_paid": is_paid,
                    "price": price,
                    "url": f"https://note.com/{user_id}/n/{note_key}",
                }
            )

            if is_paid:
                user_paid += 1
                paid_count += 1

        collected_users.add(user_id)
        print(f"    → 有料記事: {user_paid}件")

        # 進捗保存
        progress["collected_users"] = list(collected_users)
        save_progress(progress)

        time.sleep(SLEEP_TIME)

    # =====================
    # STEP 4: 保存と分析
    # =====================
    df = pd.DataFrame(all_data)

    if not df.empty:
        # 実力スコア順にソート
        df = df.sort_values("power_score", ascending=False)

        # CSV保存
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

        end_time = datetime.now()
        elapsed = end_time - start_time

        print("\n" + "=" * 70)
        print("【収集完了サマリー】")
        print("=" * 70)
        print(f"実行時間: {elapsed}")
        print(f"総記事数: {len(df)}件")
        print(f"有料記事数: {df['is_paid'].sum()}件")
        print(f"ユーザー数: {df['user_id'].nunique()}人")
        print(f"平均Power Score: {df['power_score'].mean():.4f}")

        print("\n【実力スコア上位15件】")
        print("-" * 70)
        top = df.head(15)
        for idx, row in top.iterrows():
            paid_mark = "💰" if row["is_paid"] else "  "
            title = (
                row["title"][:45] + "..." if len(row["title"]) > 45 else row["title"]
            )
            print(f"{paid_mark} [{row['power_score']:.2f}] {title}")
            print(
                f"     スキ: {row['likes']} | フォロワー: {row['followers']} | ¥{row['price']}"
            )

        print(f"\n✓ '{OUTPUT_FILE}' に保存しました。")
        print(
            f"✓ 進捗ファイル '{PROGRESS_FILE}' を削除して次回は最初から実行できます。"
        )

    return df


# ==========================================
# 実行
# ==========================================

if __name__ == "__main__":
    import sys

    # コマンドライン引数で再開/最初からを指定可能
    resume = "--fresh" not in sys.argv

    if not resume:
        # 進捗ファイルを削除
        if Path(PROGRESS_FILE).exists():
            Path(PROGRESS_FILE).unlink()
        print("🔄 進捗をリセットして最初から収集します\n")

    df = collect_data(resume=resume)
