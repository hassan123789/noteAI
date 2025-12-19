"""タグ検索APIテスト"""

import time

import requests

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("=" * 60)
print("【noteタグ・検索API調査】")
print("=" * 60)

# 様々なAPIエンドポイントをテスト
endpoints = [
    # タグ検索
    ("タグ検索(v2)", "https://note.com/api/v2/search?context=note&q=副業&size=10"),
    ("タグ検索(v3)", "https://note.com/api/v3/searches?q=副業&size=10"),
    # ハッシュタグ
    ("ハッシュタグ", "https://note.com/api/v2/hashtag/副業/notes?page=1"),
    # カテゴリ
    ("カテゴリ", "https://note.com/api/v2/categories"),
    # トピック
    ("トピック検索", "https://note.com/api/v2/topics?page=1"),
    # 人気記事
    ("人気記事", "https://note.com/api/v2/notes/popular?page=1"),
    # 新着記事
    ("新着記事", "https://note.com/api/v2/notes?page=1"),
]

for name, url in endpoints:
    print(f"\n[{name}]")
    print(f"  URL: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  ステータス: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            # データ構造を確認
            if "data" in data:
                if isinstance(data["data"], list):
                    print(f"  ✓ 成功！ 件数: {len(data['data'])}件")
                elif isinstance(data["data"], dict):
                    keys = list(data["data"].keys())[:5]
                    print(f"  ✓ 成功！ キー: {keys}")
            else:
                keys = list(data.keys())[:5]
                print(f"  ✓ 成功！ トップキー: {keys}")
        else:
            print("  ✗ 失敗")
    except Exception as e:
        print(f"  ✗ エラー: {e}")
    time.sleep(1.5)

print("\n" + "=" * 60)
print("\n" + "=" * 60)
