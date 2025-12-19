"""検索API詳細調査"""

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

    print("\n【利用可能なカーソル/キー】")
    for key in data.keys():
        print(f"  - {key}")

    # ノート（記事）データを確認
    if "note_cursor" in data:
        notes = data["note_cursor"]
        print("\n【note_cursor の構造】")
        print(f"  キー: {list(notes.keys())}")

        if "contents" in notes:
            contents = notes["contents"]
            print(f"  記事数: {len(contents)}件")

            if contents:
                print("\n【サンプル記事（1件目）の構造】")
                first = contents[0]
                for key, value in first.items():
                    if isinstance(value, (str, int, bool, float)):
                        display = (
                            str(value)[:50] + "..." if len(str(value)) > 50 else value
                        )
                        print(f"    {key}: {display}")
                    elif isinstance(value, dict):
                        print(f"    {key}: {{...}} (辞書)")
                    elif isinstance(value, list):
                        print(f"    {key}: [...] (リスト, {len(value)}件)")

                # ユーザー情報があるか確認
                if "user" in first:
                    print("\n【ユーザー情報（user）の構造】")
                    user = first["user"]
                    for key, value in user.items():
                        if isinstance(value, (str, int, bool, float)):
                            display = (
                                str(value)[:40] + "..."
                                if len(str(value)) > 40
                                else value
                            )
                            print(f"    {key}: {display}")

    # ユーザー検索結果を確認
    if "user_cursor" in data:
        users = data["user_cursor"]
        print("\n【user_cursor の構造】")
        print(f"  キー: {list(users.keys())}")
        if "contents" in users:
            print(f"  ユーザー数: {len(users['contents'])}件")

print("\n" + "=" * 60)
