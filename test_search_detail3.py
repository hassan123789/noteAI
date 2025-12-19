"""検索API詳細調査 v3"""

import requests

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("=" * 60)
print("【note検索API v3 詳細調査】")
print("=" * 60)

url = "https://note.com/api/v3/searches?q=副業&size=20"
print(f"\nURL: {url}")

r = requests.get(url, headers=headers, timeout=10)
print(f"ステータス: {r.status_code}")

if r.status_code == 200:
    data = r.json()["data"]

    # notesの型を確認
    if "notes" in data:
        notes = data["notes"]
        print(f"\nnotesの型: {type(notes)}")

        if isinstance(notes, dict):
            print(f"notesのキー: {list(notes.keys())}")
            # contentsがあるか
            if "contents" in notes:
                contents = notes["contents"]
                print(f"contentsの型: {type(contents)}")
                print(f"記事数: {len(contents)}件")

                if contents and len(contents) > 0:
                    first = contents[0]
                    print("\n【サンプル記事の主要フィールド】")
                    for key, val in first.items():
                        if isinstance(val, (str, int, bool, float)):
                            display = str(val)[:50]
                            print(f"  {key}: {display}")
                        elif isinstance(val, dict) and key == "user":
                            print("  user: (詳細下記)")

                    if "user" in first:
                        user = first["user"]
                        print("\n【ユーザー情報】")
                        for key in [
                            "urlname",
                            "nickname",
                            "followerCount",
                            "noteCount",
                        ]:
                            if key in user:
                                print(f"  {key}: {user[key]}")

                    # 上位5件表示
                    print("\n【検索結果（上位5件）】")
                    for i, note in enumerate(contents[:5], 1):
                        title = note.get("name", "N/A")[:35]
                        likes = note.get("likeCount", 0)
                        user = note.get("user", {})
                        urlname = user.get("urlname", "?")
                        followers = user.get("followerCount", "?")
                        is_paid = note.get("isPaid", False)
                        print(f"  {i}. {title}...")
                        print(
                            f"     @{urlname} | フォロワー: {followers} | スキ: {likes} | 有料: {is_paid}"
                        )
        elif isinstance(notes, list):
            print(f"記事数: {len(notes)}件")
            if notes:
                first = notes[0]
                print(f"1件目の型: {type(first)}")
                if isinstance(first, dict):
                    print(f"キー: {list(first.keys())}")

print("\n" + "=" * 60)
