"""
note特化型AI開発プロジェクト - 完全版データ収集スクリプト

【確認済みAPI】
1. ユーザー情報API: https://note.com/api/v2/creators/{user_id}
   - フォロワー数、記事数など取得可能

2. 記事一覧API: https://note.com/api/v2/creators/{user_id}/contents?kind=note&page=1
   - タイトル、スキ数、有料かどうか取得可能

3. 検索API: https://note.com/api/v3/searches?q={keyword}&size=20
   - キーワード検索で記事とユーザーを発見可能
   - ※フォロワー数は含まれないため、別途取得が必要

【使用方法】
1. キーワード検索でユーザーを発見
2. 各ユーザーのフォロワー数を確認
3. 条件に合うユーザーの記事を収集
4. 「実力スコア」を計算してCSV出力
"""

import time
from typing import Optional

import pandas as pd
import requests

# ==========================================
# 設定
# ==========================================

# 検索キーワード（複数指定可能）
SEARCH_KEYWORDS = [
    "副業",
    "ブログ",
    "稼ぐ",
]

# フォロワー数の条件
MIN_FOLLOWERS = 10  # 最低フォロワー数（少なすぎる人は除外）
MAX_FOLLOWERS = 1000  # 最大フォロワー数（インフルエンサー除外）

# 1キーワードあたりの検索結果数
SEARCH_SIZE = 50

# APIアクセス間隔（秒）
SLEEP_TIME = 2.0

# 共通ヘッダー
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


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


def get_user_notes(user_id: str, max_pages: int = 10) -> list:
    """ユーザーの全記事を取得"""
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


def search_notes(keyword: str, size: int = 50) -> list:
    """キーワードで記事を検索し、ユーザーIDリストを取得"""
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


def collect_data() -> pd.DataFrame:
    """完全なデータ収集フロー"""

    print("=" * 60)
    print("【note特化型AI データ収集開始】")
    print("=" * 60)

    # ステップ1: 検索でユーザーを発見
    print("\n[STEP 1] キーワード検索でユーザーを発見中...")
    discovered_users = set()

    for keyword in SEARCH_KEYWORDS:
        print(f"  検索中: 「{keyword}」")
        notes = search_notes(keyword, SEARCH_SIZE)

        for note in notes:
            user = note.get("user", {})
            urlname = user.get("urlname")
            if urlname:
                discovered_users.add(urlname)

        print(f"    → {len(notes)}件の記事から{len(discovered_users)}人を発見")
        time.sleep(SLEEP_TIME)

    print(f"\n  合計発見ユーザー数: {len(discovered_users)}人")

    # ステップ2: 各ユーザーのフォロワー数を確認
    print("\n[STEP 2] フォロワー数を確認中...")
    target_users = []

    for i, user_id in enumerate(discovered_users, 1):
        if i % 10 == 0:
            print(f"  進捗: {i}/{len(discovered_users)}")

        user_info = get_user_info(user_id)
        if user_info:
            followers = user_info.get("followerCount", 0)

            # フォロワー数で絞り込み
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

    print(f"\n  条件に合うユーザー: {len(target_users)}人")
    print(f"  （{MIN_FOLLOWERS}〜{MAX_FOLLOWERS}フォロワー）")

    if not target_users:
        print("\n条件に合うユーザーが見つかりませんでした。")
        return pd.DataFrame()

    # ステップ3: 記事データを収集
    print("\n[STEP 3] 記事データを収集中...")
    all_data = []

    for i, user in enumerate(target_users, 1):
        user_id = user["user_id"]
        followers = user["followers"]
        nickname = user["nickname"]

        print(
            f"  [{i}/{len(target_users)}] @{user_id} ({nickname}) - {followers}フォロワー"
        )

        notes = get_user_notes(user_id)

        for note in notes:
            title = note.get("name", "")
            likes = note.get("likeCount", 0)
            is_paid = note.get("isPaid", False)
            note_key = note.get("key", "")

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
                    "url": f"https://note.com/{user_id}/n/{note_key}",
                }
            )

        print(f"    → {len(notes)}件の記事を取得")
        time.sleep(SLEEP_TIME)

    df = pd.DataFrame(all_data)

    # ステップ4: 分析と保存
    print("\n[STEP 4] データを分析・保存中...")

    if not df.empty:
        # 実力スコア順にソート
        df = df.sort_values("power_score", ascending=False)

        # CSVに保存
        output_file = "note_power_data.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")

        print("\n" + "=" * 60)
        print("【収集完了サマリー】")
        print("=" * 60)
        print(f"総記事数: {len(df)}件")
        print(f"ユーザー数: {df['user_id'].nunique()}人")
        print(f"有料記事数: {df['is_paid'].sum()}件")

        print("\n【実力スコア上位10件】（フォロワー比でスキが多い記事）")
        top_10 = df.head(10)[["title", "likes", "followers", "power_score", "is_paid"]]
        for i, row in top_10.iterrows():
            title = row["title"][:40]
            print(f"  {title}...")
            print(
                f"    スキ: {row['likes']} | フォロワー: {row['followers']} | スコア: {row['power_score']:.2f}"
            )

        print(f"\n✓ '{output_file}' に保存しました。")

    return df


# ==========================================
# 実行
# ==========================================

if __name__ == "__main__":
    df = collect_data()
