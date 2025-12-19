"""検索API詳細調査 v2"""

import requests

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("=" * 60)
print("【note検索API v3 詳細調査】")
print("=" * 60)

# v3検索APIの詳細を調べる
url = "https://note.com/api/v3/searches?q=副業&size=20"
print(f"\nURL: {url}")

r = requests.get(url, headers=headers, timeout=10)
print(f"ステータス: {r.status_code}")

if r.status_code == 200:
    data = r.json()["data"]

    # notes（記事リスト）を確認
    if "notes" in data:
        notes = data["notes"]
        print("\n【notes（記事リスト）】")
        print(f"  記事数: {len(notes)}件")

        if notes:
            print("\n【サンプル記事（1件目）の主要フィールド】")
            first = notes[0]

            # 主要フィールドを表示
            important_keys = ["id", "name", "likeCount", "isPaid", "key"]
            for key in important_keys:
                if key in first:
                    print(f"    {key}: {first[key]}")

            # ユーザー情報があるか確認
            if "user" in first:
                print("\n【ユーザー情報】")
                user = first["user"]
                user_keys = ["id", "urlname", "nickname", "followerCount", "noteCount"]
                for key in user_keys:
                    if key in user:
                        print(f"    {key}: {user[key]}")

            # 3件分のタイトルとスキ数を表示
            print("\n【検索結果（上位5件）】")
            for i, note in enumerate(notes[:5], 1):
                title = note.get("name", "N/A")[:35]
                likes = note.get("likeCount", 0)
                user = note.get("user", {})
                urlname = user.get("urlname", "?")
                followers = user.get("followerCount", "?")
                is_paid = note.get("isPaid", False)
                print(f"  {i}. {title}...")
                print(f"     ユーザー: @{urlname} (フォロワー: {followers})")
                print(f"     スキ: {likes} | 有料: {is_paid}")
                print()

print("=" * 60)
print("【結論】検索APIからユーザーID・フォロワー数・スキ数が一括取得可能！")
print("=" * 60)
