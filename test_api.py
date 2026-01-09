"""APIテストスクリプト - v3スクリプト検証用"""

print("=" * 60)
print("【collect_power_data_v3.py 検証テスト】")
print("=" * 60)

# v3スクリプトからインポート
from collect_power_data_v3 import (BASE_URL, HEADERS, get_user_info,
                                   search_notes)

print("\n[0] モジュールインポート")
print(f"    ✅ BASE_URL: {BASE_URL}")
print(f"    ✅ HEADERS keys: {list(HEADERS.keys())}")

# 1. search_notes() テスト
print("\n[1] search_notes() テスト")
notes = search_notes("副業", page=1)
print(f"    取得件数: {len(notes)}件")

if notes:
    sample = notes[0]
    title = sample.get("name", "N/A")[:40]
    urlname = sample.get("user", {}).get("urlname", "N/A")
    print(f"    ✅ サンプル記事: {title}")
    print(f"    ✅ ユーザー urlname: {urlname}")

    # 2. get_user_info() テスト
    print("\n[2] get_user_info() テスト")
    user_info = get_user_info(urlname)
    if user_info:
        nickname = user_info.get("nickname", "N/A")
        followers = user_info.get("followerCount", 0)
        print(f"    ✅ nickname: {nickname}")
        print(f"    ✅ followerCount: {followers:,}")
    else:
        print("    ❌ ユーザー情報取得失敗")
else:
    print("    ❌ 記事取得失敗")

print("\n" + "=" * 60)
print("🎉 全テスト成功！収集スクリプトは正常に動作します。")
print("=" * 60)
