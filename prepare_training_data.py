"""
note.com タイトル学習データ準備スクリプト
==========================================
Phase 2: データ分析 → クレンジング → 学習データ生成

生成物:
- training_data.jsonl: Fine-tuning用データ
- data_report.txt: データ品質レポート
"""

import json
import re
from datetime import datetime

import pandas as pd

# ============================================================
# 設定
# ============================================================
INPUT_CSV = "note_power_data.csv"
OUTPUT_JSONL = "training_data.jsonl"
OUTPUT_REPORT = "data_report.txt"

# Power Score閾値（これ以上を「成功タイトル」とする）
SUCCESS_THRESHOLD = 1.0  # 1.0以上 = フォロワー数以上のスキを獲得

# 除外条件（緩和版：タイトルパターン学習に不要なもののみ）
EXCLUDE_PATTERNS = [
    r"^サイトマップ$",  # 目次系のみ
    r"^マガジン",  # 非記事系
    r"^おはよう朝ふみ",  # 定型連載（冒頭のみ）
]

# 最低スキ数（ノイズ除去）- 緩和
MIN_LIKES = 10


# ============================================================
# データ分析関数
# ============================================================
def analyze_data(df: pd.DataFrame) -> dict:
    """データの詳細分析"""
    stats = {
        "total_records": len(df),
        "unique_users": df["user_id"].nunique(),
        "power_score": {
            "mean": df["power_score"].mean(),
            "median": df["power_score"].median(),
            "std": df["power_score"].std(),
            "min": df["power_score"].min(),
            "max": df["power_score"].max(),
            "q25": df["power_score"].quantile(0.25),
            "q75": df["power_score"].quantile(0.75),
        },
        "likes": {
            "mean": df["likes"].mean(),
            "median": df["likes"].median(),
            "min": df["likes"].min(),
            "max": df["likes"].max(),
        },
        "followers_dist": df["followers"].describe().to_dict(),
        "top_users": df.groupby("user_id")["power_score"].mean().nlargest(10).to_dict(),
        "title_length": {
            "mean": df["title"].str.len().mean(),
            "min": df["title"].str.len().min(),
            "max": df["title"].str.len().max(),
        },
    }
    return stats


def extract_title_features(title: str) -> dict:
    """タイトルから特徴を抽出"""
    features = {
        "length": len(title),
        "has_brackets": bool(re.search(r"[【】「」『』\[\]]", title)),
        "has_numbers": bool(re.search(r"\d+", title)),
        "has_emoji": bool(
            re.search(r"[😀-🙏🌀-🗿🚀-🛿🇦-🇿✂-➰🔀-🔿🕐-🕧🖐-🗑🤐-🧿🩰-🫶]", title)
        ),
        "has_question": "?" in title or "？" in title,
        "has_exclamation": "!" in title or "！" in title,
        "has_pipe": "|" in title or "｜" in title,
        "word_count": len(title.split()),
        "has_money_term": bool(re.search(r"(稼|万円|収益|月収|副業|収入)", title)),
        "has_action_verb": bool(
            re.search(r"(やってみた|してみた|試した|始め|挑戦)", title)
        ),
    }
    return features


# ============================================================
# データクレンジング
# ============================================================
def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """データクレンジング処理"""
    original_count = len(df)
    removal_log = {"original": original_count, "steps": []}

    # Step 1: 除外パターンに該当するタイトルを除去
    pattern = "|".join(EXCLUDE_PATTERNS)
    mask = ~df["title"].str.contains(pattern, case=False, regex=True, na=False)
    removed = len(df) - mask.sum()
    df = df[mask].copy()
    removal_log["steps"].append(
        {"step": "除外パターン", "removed": removed, "remaining": len(df)}
    )

    # Step 2: 最低スキ数未満を除去
    mask = df["likes"] >= MIN_LIKES
    removed = len(df) - mask.sum()
    df = df[mask].copy()
    removal_log["steps"].append(
        {
            "step": f"最低スキ数({MIN_LIKES}未満)",
            "removed": removed,
            "remaining": len(df),
        }
    )

    # Step 3: 重複タイトル除去
    before = len(df)
    df = df.drop_duplicates(subset=["title"])
    removed = before - len(df)
    removal_log["steps"].append(
        {"step": "重複タイトル", "removed": removed, "remaining": len(df)}
    )

    # Step 4: 極端な外れ値の確認（削除はしないが記録）
    high_outliers = df[df["power_score"] > 10]
    if len(high_outliers) > 0:
        removal_log["outliers"] = {
            "high_power_score": len(high_outliers),
            "samples": high_outliers["title"].head(5).tolist(),
        }

    removal_log["final"] = len(df)
    removal_log["removed_total"] = original_count - len(df)
    removal_log["retention_rate"] = len(df) / original_count * 100

    return df, removal_log


# ============================================================
# 学習データ生成
# ============================================================
def create_training_data(df: pd.DataFrame) -> list[dict]:
    """JSOLNフォーマットの学習データ生成"""
    training_data = []

    for _, row in df.iterrows():
        # 成功/失敗ラベル
        is_success = row["power_score"] >= SUCCESS_THRESHOLD

        # 特徴抽出
        features = extract_title_features(row["title"])

        # 学習用レコード
        record = {
            # メタ情報
            "id": f"{row['user_id']}_{hash(row['title']) % 10000:04d}",
            # 入力（タイトル）
            "title": row["title"],
            # ラベル
            "label": "success" if is_success else "normal",
            "power_score": round(row["power_score"], 4),
            # 補助情報
            "likes": int(row["likes"]),
            "followers": int(row["followers"]),
            # 特徴
            "features": features,
            # プロンプト形式（Fine-tuning用）
            "prompt": f"以下の条件でnote記事のタイトルを評価してください。\nタイトル: {row['title']}\n\n評価:",
            "completion": f" {'高エンゲージメント' if is_success else '標準'}（スコア: {row['power_score']:.2f}）",
        }

        training_data.append(record)

    return training_data


def create_title_generation_data(df: pd.DataFrame) -> list[dict]:
    """タイトル生成学習用データ（成功例のみ）"""
    success_df = df[df["power_score"] >= SUCCESS_THRESHOLD].copy()
    generation_data = []

    for _, row in success_df.iterrows():
        # キーワード抽出（簡易版）
        title = row["title"]

        # タイトルからキーワードを推測
        keywords = []
        if re.search(r"副業|稼ぐ|収益", title):
            keywords.append("副業・収益系")
        if re.search(r"AI|ChatGPT|Sora|生成", title):
            keywords.append("AI・テクノロジー")
        if re.search(r"子育て|育児|ママ|パパ", title):
            keywords.append("育児・家族")
        if re.search(r"自分|人生|生き", title):
            keywords.append("自己啓発")
        if not keywords:
            keywords.append("その他")

        record = {
            "instruction": f"「{', '.join(keywords)}」に関する、読者の興味を引くnote記事タイトルを生成してください。",
            "input": "",
            "output": title,
            "power_score": round(row["power_score"], 4),
            "likes": int(row["likes"]),
        }

        generation_data.append(record)

    return generation_data


# ============================================================
# レポート生成
# ============================================================
def generate_report(
    stats: dict, removal_log: dict, training_data: list, generation_data: list
) -> str:
    """データ品質レポート生成"""
    report = []
    report.append("=" * 60)
    report.append("note.com タイトル学習データ - 品質レポート")
    report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)

    report.append("\n## 1. 元データ統計")
    report.append(f"- 総レコード数: {stats['total_records']}")
    report.append(f"- ユニークユーザー数: {stats['unique_users']}")
    report.append(
        f"- Power Score: 平均 {stats['power_score']['mean']:.2f}, 中央値 {stats['power_score']['median']:.2f}"
    )
    report.append(f"  - 最小: {stats['power_score']['min']:.4f}")
    report.append(f"  - 最大: {stats['power_score']['max']:.2f}")
    report.append(f"  - 25%点: {stats['power_score']['q25']:.2f}")
    report.append(f"  - 75%点: {stats['power_score']['q75']:.2f}")

    report.append("\n## 2. クレンジング結果")
    report.append(f"- 元データ: {removal_log['original']} 件")
    for step in removal_log["steps"]:
        report.append(
            f"  - {step['step']}: -{step['removed']} → 残り {step['remaining']} 件"
        )
    report.append(f"- 最終データ: {removal_log['final']} 件")
    report.append(f"- 保持率: {removal_log['retention_rate']:.1f}%")

    if "outliers" in removal_log:
        report.append(
            f"\n### 外れ値（Power Score > 10）: {removal_log['outliers']['high_power_score']} 件"
        )
        for sample in removal_log["outliers"]["samples"]:
            report.append(f"  - {sample[:50]}...")

    report.append("\n## 3. 学習データ統計")
    success_count = sum(1 for d in training_data if d["label"] == "success")
    normal_count = len(training_data) - success_count
    report.append(f"- 評価モデル用: {len(training_data)} 件")
    report.append(
        f"  - 成功ラベル: {success_count} 件 ({success_count / len(training_data) * 100:.1f}%)"
    )
    report.append(
        f"  - 通常ラベル: {normal_count} 件 ({normal_count / len(training_data) * 100:.1f}%)"
    )
    report.append(f"- 生成モデル用: {len(generation_data)} 件（成功例のみ）")

    report.append("\n## 4. タイトル特徴分析（成功例）")
    success_data = [d for d in training_data if d["label"] == "success"]
    if success_data:
        bracket_count = sum(1 for d in success_data if d["features"]["has_brackets"])
        number_count = sum(1 for d in success_data if d["features"]["has_numbers"])
        money_count = sum(1 for d in success_data if d["features"]["has_money_term"])
        question_count = sum(1 for d in success_data if d["features"]["has_question"])

        report.append(
            f"- 【】等の括弧使用: {bracket_count} 件 ({bracket_count / len(success_data) * 100:.1f}%)"
        )
        report.append(
            f"- 数字使用: {number_count} 件 ({number_count / len(success_data) * 100:.1f}%)"
        )
        report.append(
            f"- 金銭関連ワード: {money_count} 件 ({money_count / len(success_data) * 100:.1f}%)"
        )
        report.append(
            f"- 疑問形: {question_count} 件 ({question_count / len(success_data) * 100:.1f}%)"
        )

        avg_length = sum(d["features"]["length"] for d in success_data) / len(
            success_data
        )
        report.append(f"- 平均文字数: {avg_length:.1f} 文字")

    report.append("\n## 5. Top 10 成功タイトル")
    sorted_data = sorted(training_data, key=lambda x: x["power_score"], reverse=True)[
        :10
    ]
    for i, d in enumerate(sorted_data, 1):
        report.append(f"{i}. [{d['power_score']:.2f}] {d['title'][:50]}...")

    report.append("\n" + "=" * 60)
    report.append("レポート終了")
    report.append("=" * 60)

    return "\n".join(report)


# ============================================================
# メイン処理
# ============================================================
def main():
    print("=" * 60)
    print("Phase 2: 学習データ準備開始")
    print("=" * 60)

    # 1. データ読み込み
    print("\n[1/5] データ読み込み中...")
    df = pd.read_csv(INPUT_CSV)
    print(f"  → {len(df)} 件のレコードを読み込み")

    # 2. データ分析
    print("\n[2/5] データ分析中...")
    stats = analyze_data(df)
    print(
        f"  → Power Score: 平均 {stats['power_score']['mean']:.2f}, 中央値 {stats['power_score']['median']:.2f}"
    )

    # 3. クレンジング
    print("\n[3/5] データクレンジング中...")
    cleaned_df, removal_log = clean_data(df)
    print(
        f"  → {removal_log['original']} → {removal_log['final']} 件 (保持率: {removal_log['retention_rate']:.1f}%)"
    )

    # 4. 学習データ生成
    print("\n[4/5] 学習データ生成中...")
    training_data = create_training_data(cleaned_df)
    generation_data = create_title_generation_data(cleaned_df)

    success_count = sum(1 for d in training_data if d["label"] == "success")
    print(
        f"  → 評価用: {len(training_data)} 件 (成功: {success_count}, 通常: {len(training_data) - success_count})"
    )
    print(f"  → 生成用: {len(generation_data)} 件")

    # 5. ファイル出力
    print("\n[5/5] ファイル出力中...")

    # JSONL出力（評価モデル用）
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for record in training_data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  → {OUTPUT_JSONL} を出力")

    # JSONL出力（生成モデル用）
    generation_jsonl = "generation_training.jsonl"
    with open(generation_jsonl, "w", encoding="utf-8") as f:
        for record in generation_data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  → {generation_jsonl} を出力")

    # レポート出力
    report = generate_report(stats, removal_log, training_data, generation_data)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"  → {OUTPUT_REPORT} を出力")

    # 完了
    print("\n" + "=" * 60)
    print("Phase 2 完了!")
    print("=" * 60)
    print("\n生成ファイル:")
    print(f"  - {OUTPUT_JSONL}: 評価モデル学習用")
    print(f"  - {generation_jsonl}: 生成モデル学習用")
    print(f"  - {OUTPUT_REPORT}: データ品質レポート")
    print("\n次のステップ: Phase 3 - モデル学習 (Google Colabで実行)")


if __name__ == "__main__":
    main()
    main()
