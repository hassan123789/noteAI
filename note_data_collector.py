"""
note特化型AI開発プロジェクト - Phase 1: データ収集スクリプト

目的:
- noteの内部APIを使用して記事データを収集
- 「フォロワーが少ないのに、スキが多い」記事を抽出
- タイトル生成AIの学習データを作成

使用方法:
1. TARGET_USERSにユーザーIDを追加
2. スクリプトを実行
3. note_data.csvが生成される

注意事項:
- アクセス間隔を守ること（サーバー負荷軽減）
- 学習・研究目的での使用に限定すること
"""

import time

import pandas as pd
import requests

# ==========================================
# 設定エリア（ここを変更）
# ==========================================

# 調べたいユーザーのID（URLの note.com/xxxx の xxxx の部分）
# 手動で追加するか、後述のsearch_users_by_tag()で自動収集できます
TARGET_USERS = [
    # テスト用のサンプルユーザー（フォロワー数が少なめのクリエイター）
    # 実際の運用時は自分でリストを作成するか、タグ検索で自動収集
]

# このフォロワー数以上の人は「インフルエンサー」とみなして無視する
FOLLOWER_THRESHOLD = 1000

# APIにアクセスする間隔（秒）。短すぎるとBANされます。最低2秒は空けること。
SLEEP_TIME = 2.0


# ==========================================
# 共通のHTTPヘッダー（ブラウザを偽装）
# ==========================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


# ==========================================
# API検証関数（まずこれを実行してAPIの存在を確認）
# ==========================================
def verify_api_exists(test_user_id: str = "note") -> dict:
    """
    noteの内部APIが本当に存在するか検証する。
    デフォルトでnote公式アカウントを使用。
    """
    print("=" * 50)
    print("【API存在確認テスト】")
    print("=" * 50)

    result = {"profile_api": False, "contents_api": False, "sample_data": None}

    # 1. ユーザープロフィールAPI
    url_profile = f"https://note.com/api/v2/creators/{test_user_id}"
    print(f"\n[1] プロフィールAPI: {url_profile}")

    try:
        res = requests.get(url_profile, headers=HEADERS, timeout=10)
        print(f"    ステータスコード: {res.status_code}")

        if res.status_code == 200:
            data = res.json()
            if "data" in data:
                result["profile_api"] = True
                user_data = data["data"]
                print("    ✓ APIは存在します！")
                print(f"    ユーザー名: {user_data.get('nickname', 'N/A')}")
                print(f"    フォロワー数: {user_data.get('followerCount', 'N/A')}")
                print(f"    記事数: {user_data.get('noteCount', 'N/A')}")
        else:
            print("    ✗ アクセス失敗")

    except Exception as e:
        print(f"    ✗ エラー: {e}")

    time.sleep(SLEEP_TIME)

    # 2. 記事一覧API
    url_contents = (
        f"https://note.com/api/v2/creators/{test_user_id}/contents?kind=note&page=1"
    )
    print(f"\n[2] 記事一覧API: {url_contents}")

    try:
        res = requests.get(url_contents, headers=HEADERS, timeout=10)
        print(f"    ステータスコード: {res.status_code}")

        if res.status_code == 200:
            data = res.json()
            if "data" in data and "contents" in data["data"]:
                result["contents_api"] = True
                contents = data["data"]["contents"]
                print("    ✓ APIは存在します！")
                print(f"    取得記事数: {len(contents)}件")

                if contents:
                    first_note = contents[0]
                    result["sample_data"] = {
                        "title": first_note.get("name", "N/A"),
                        "likeCount": first_note.get("likeCount", 0),
                        "isPaid": first_note.get("isPaid", False),
                    }
                    print("\n    【サンプルデータ】")
                    print(f"    タイトル: {result['sample_data']['title'][:50]}...")
                    print(f"    スキ数: {result['sample_data']['likeCount']}")
                    print(f"    有料記事: {result['sample_data']['isPaid']}")
        else:
            print("    ✗ アクセス失敗")

    except Exception as e:
        print(f"    ✗ エラー: {e}")

    # 結論
    print("\n" + "=" * 50)
    if result["profile_api"] and result["contents_api"]:
        print("【結論】内部APIは実在します。データ収集が可能です。")
    else:
        print("【結論】APIへのアクセスに問題があります。")
    print("=" * 50)

    return result


# ==========================================
# メインのデータ収集関数
# ==========================================
def collect_note_data(user_ids: list) -> pd.DataFrame:
    """
    指定したユーザーIDリストから記事データを収集する。
    インフルエンサー（フォロワー数が閾値以上）は自動でスキップ。
    """
    if not user_ids:
        print("エラー: TARGET_USERSが空です。ユーザーIDを追加してください。")
        return pd.DataFrame()

    all_data = []

    for idx, user_id in enumerate(user_ids, 1):
        print(f"\n[{idx}/{len(user_ids)}] @{user_id} を調査中...")

        # --- A. ユーザー情報を取得（フォロワー数チェック） ---
        url_profile = f"https://note.com/api/v2/creators/{user_id}"

        try:
            res_profile = requests.get(url_profile, headers=HEADERS, timeout=10)

            if res_profile.status_code != 200:
                print(
                    f"    ✗ ユーザーが見つかりません (Status: {res_profile.status_code})"
                )
                time.sleep(SLEEP_TIME)
                continue

            data_profile = res_profile.json()["data"]
            follower_count = data_profile.get("followerCount", 0)
            nickname = data_profile.get("nickname", user_id)

            # インフルエンサーならスキップ（API節約）
            if follower_count > FOLLOWER_THRESHOLD:
                print(
                    f"    → フォロワー{follower_count:,}人のためスキップ（インフルエンサー除外）"
                )
                time.sleep(SLEEP_TIME)
                continue

            print(
                f"    → フォロワー{follower_count:,}人（{nickname}）。記事を収集中..."
            )

        except Exception as e:
            print(f"    ✗ エラー発生: {e}")
            time.sleep(SLEEP_TIME)
            continue

        time.sleep(SLEEP_TIME)

        # --- B. 記事一覧を取得 ---
        page = 1
        has_next = True
        user_note_count = 0

        while has_next:
            url_contents = f"https://note.com/api/v2/creators/{user_id}/contents?kind=note&page={page}"

            try:
                res_contents = requests.get(url_contents, headers=HEADERS, timeout=10)

                if res_contents.status_code != 200:
                    break

                data_contents = res_contents.json()["data"]
                notes = data_contents.get("contents", [])

                if not notes:
                    break

                for note in notes:
                    title = note.get("name", "")
                    like_count = note.get("likeCount", 0)
                    note_key = note.get("key", "")
                    is_paid = note.get("isPaid", False)
                    published_at = note.get("publishAt", "")

                    # 実力スコア = スキ数 ÷ フォロワー数
                    power_score = (
                        round(like_count / follower_count, 4)
                        if follower_count > 0
                        else 0
                    )

                    all_data.append(
                        {
                            "user_id": user_id,
                            "nickname": nickname,
                            "followers": follower_count,
                            "title": title,
                            "likes": like_count,
                            "power_score": power_score,
                            "is_paid": is_paid,
                            "published_at": published_at,
                            "url": f"https://note.com/{user_id}/n/{note_key}",
                        }
                    )
                    user_note_count += 1

                # 次のページがあるか確認
                if data_contents.get("isLastPage", True):
                    has_next = False
                else:
                    page += 1
                    time.sleep(SLEEP_TIME)

            except Exception as e:
                print(f"    ✗ 記事取得エラー: {e}")
                break

        print(f"    ✓ {user_note_count}件の記事を取得しました")
        time.sleep(SLEEP_TIME)

    return pd.DataFrame(all_data)


# ==========================================
# 結果の分析・保存
# ==========================================
def analyze_and_save(df: pd.DataFrame, output_file: str = "note_data.csv"):
    """
    収集したデータを分析し、CSVに保存する。
    """
    if df.empty:
        print("データが空です。")
        return

    print("\n" + "=" * 50)
    print("【収集結果サマリー】")
    print("=" * 50)
    print(f"総記事数: {len(df)}件")
    print(f"ユーザー数: {df['user_id'].nunique()}人")
    print(f"有料記事数: {df['is_paid'].sum()}件")

    # 実力スコア上位を表示
    print("\n【実力スコア上位10件】（フォロワー比でスキが多い記事）")
    top_10 = df.nlargest(10, "power_score")[
        ["title", "likes", "followers", "power_score", "is_paid"]
    ]
    print(top_10.to_string(index=False))

    # CSVに保存
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n✓ '{output_file}' に保存しました。")

    return df


# ==========================================
# メイン実行
# ==========================================
if __name__ == "__main__":
    # まずAPIの存在を確認
    print("\n")
    result = verify_api_exists()

    if result["profile_api"] and result["contents_api"]:
        print("\n\nAPIが確認できました。次にTARGET_USERSにユーザーIDを追加して、")
        print("再度スクリプトを実行すると、データ収集が開始されます。")

        # TARGET_USERSが設定されていれば収集を開始
        if TARGET_USERS:
            print("\n\n")
            df = collect_note_data(TARGET_USERS)
            if not df.empty:
                analyze_and_save(df)
