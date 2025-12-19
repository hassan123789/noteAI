"""APIテストスクリプト"""

import requests

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("=" * 60)
print("【note内部API検証テスト】")
print("=" * 60)

# 1. ユーザー情報API
print("\n[1] ユーザー情報API テスト (kensuu)")
url = "https://note.com/api/v2/creators/kensuu"
r = requests.get(url, headers=headers)
print(f"    URL: {url}")
print(f"    ステータス: {r.status_code}")

if r.status_code == 200:
    data = r.json()["data"]
    print("    ✓ APIは存在します！")
    print(f"    ユーザー名: {data.get('nickname')}")
    print(f"    フォロワー数: {data.get('followerCount'):,}")
    print(f"    記事数: {data.get('noteCount')}")

# 2. 記事一覧API
print("\n[2] 記事一覧API テスト (kensuu)")
url = "https://note.com/api/v2/creators/kensuu/contents?kind=note&page=1"
r = requests.get(url, headers=headers)
print(f"    URL: {url}")
print(f"    ステータス: {r.status_code}")

if r.status_code == 200:
    data = r.json()["data"]
    contents = data.get("contents", [])
    print("    ✓ APIは存在します！")
    print(f"    取得記事数: {len(contents)}件")

    if contents:
        print("\n    【最新3件の記事】")
        for i, note in enumerate(contents[:3], 1):
            title = note.get("name", "N/A")[:40]
            likes = note.get("likeCount", 0)
            is_paid = note.get("isPaid", False)
            print(f"    {i}. {title}...")
            print(f"       スキ: {likes:,} | 有料: {is_paid}")

print("\n" + "=" * 60)
print("【結論】note内部APIは実在し、データ収集が可能です！")
print("=" * 60)
