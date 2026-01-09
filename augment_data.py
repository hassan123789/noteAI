"""
noteAI 合成データ生成スクリプト
2026年世界最高水準版

機能:
- Self-Instructによるデータ拡張
- Evol-Instructによる複雑化
- タイトルパターンの変形生成
- 品質フィルタリング
"""

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

# ============================================================
# 設定
# ============================================================

DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
AUGMENTED_DIR = DATA_DIR / "augmented"

INPUT_FILE = PROCESSED_DIR / "training_data_v2.jsonl"
OUTPUT_FILE = AUGMENTED_DIR / "augmented_training.jsonl"
EVOL_OUTPUT_FILE = AUGMENTED_DIR / "evol_augmented.jsonl"

# 拡張設定
AUGMENT_CONFIG = {
    "target_examples": 500,      # 目標例数
    "variations_per_example": 3,  # 1例あたりの変形数
    "use_llm": False,            # LLM使用（APIキー必要）
}

# ============================================================
# テンプレートベース拡張（LLMなし）
# ============================================================

# タイトルパターンテンプレート
TITLE_TEMPLATES = {
    "question": [
        "なぜ{keyword}で{result}できたのか？",
        "{keyword}って{question}なの？",
        "どうして{action}すると{result}になるのか",
        "{keyword}で悩んでいませんか？",
    ],
    "number_list": [
        "{keyword}で成功する{num}つの方法",
        "【{num}選】{keyword}のおすすめ{category}",
        "{keyword}を始める前に知っておくべき{num}つのこと",
        "{action}するための{num}ステップ",
    ],
    "how_to": [
        "{keyword}の始め方【初心者向け】",
        "{action}する方法を徹底解説",
        "誰でもできる{keyword}のコツ",
        "{keyword}を成功させる具体的な手順",
    ],
    "experience": [
        "{period}{action}してみた結果",
        "{keyword}を{period}続けてわかったこと",
        "【体験記】{action}したら{result}になった",
        "{keyword}に挑戦して{num}ヶ月が経ちました",
    ],
    "confession": [
        "{action}した話",
        "{keyword}で{result}になった話",
        "私が{action}を決意した理由",
        "{keyword}について本音で語る",
    ],
    "negative": [
        "{keyword}をやめたら{result}になった",
        "なぜ私は{action}をしないのか",
        "{keyword}で失敗した{num}つの原因",
        "{action}しない方がいい理由",
    ],
    "transformation": [
        "{before}から{after}に変わった方法",
        "{keyword}で人生が変わった",
        "{period}で{result}を達成した全記録",
        "ダメダメだった私が{result}できるようになるまで",
    ],
}

# 埋め込み用の語彙
VOCABULARY = {
    "keyword": [
        "副業", "投資", "英語学習", "プログラミング", "ブログ", "YouTube",
        "転職", "起業", "フリーランス", "資産形成", "読書", "筋トレ",
        "瞑想", "朝活", "時短術", "ミニマリスト", "自己投資", "習慣化",
    ],
    "action": [
        "始める", "やめる", "続ける", "挑戦する", "学ぶ", "実践する",
        "変える", "捨てる", "手放す", "取り入れる", "見直す",
    ],
    "result": [
        "成功", "収益化", "月10万円", "自由な時間", "心の余裕",
        "フォロワー1000人", "PV10倍", "人生が変わる", "スキルアップ",
    ],
    "period": [
        "1週間", "1ヶ月", "3ヶ月", "半年", "1年", "100日",
    ],
    "num": ["3", "5", "7", "10", "12", "15", "20", "30", "50", "100"],
    "before": ["会社員", "初心者", "素人", "ゼロ", "マイナス"],
    "after": ["フリーランス", "プロ", "専門家", "月収100万", "独立"],
    "question": ["本当", "効果的", "意味がある", "必要", "おすすめ"],
    "category": ["ツール", "方法", "書籍", "サービス", "アプリ"],
}

def fill_template(template: str) -> str:
    """テンプレートを埋める"""
    result = template
    for key, values in VOCABULARY.items():
        placeholder = "{" + key + "}"
        while placeholder in result:
            result = result.replace(placeholder, random.choice(values), 1)
    return result

def generate_template_variations(pattern: str, count: int = 5) -> List[str]:
    """テンプレートからバリエーションを生成"""
    if pattern not in TITLE_TEMPLATES:
        return []

    templates = TITLE_TEMPLATES[pattern]
    variations = []

    for _ in range(count):
        template = random.choice(templates)
        variation = fill_template(template)
        if variation not in variations:
            variations.append(variation)

    return variations[:count]

# ============================================================
# Evol-Instruct 複雑化
# ============================================================

def evolve_instruction_depth(instruction: str) -> str:
    """指示を深化（より詳細に）"""
    additions = [
        "特に、読者の感情を動かす要素を含めてください。",
        "SEOを意識しつつも、クリック率を高める工夫を入れてください。",
        "タイトルの最初の5文字で読者の注意を引くことを意識してください。",
        "具体的な数字や期間を含めると効果的です。",
        "読者が「自分ごと」として捉えられる表現を使ってください。",
    ]
    return instruction + " " + random.choice(additions)

def evolve_instruction_breadth(instruction: str) -> str:
    """指示を広げる（範囲拡大）"""
    expansions = [
        "また、同じテーマで異なるアプローチのタイトル案も3つ考えてください。",
        "このタイトルを「疑問形」「体験談形」「ハウツー形」の3パターンで作成してください。",
        "初心者向けと上級者向けの2バージョンを作成してください。",
    ]
    return instruction + " " + random.choice(expansions)

def evolve_add_constraints(instruction: str) -> str:
    """制約を追加"""
    constraints = [
        "ただし、30文字以内で収めてください。",
        "ただし、疑問形は使わないでください。",
        "ただし、数字を必ず1つ含めてください。",
        "ただし、ネガティブな表現から始めてください。",
        "ただし、括弧【】を効果的に使ってください。",
    ]
    return instruction + " " + random.choice(constraints)

def evolve_instruction(entry: Dict) -> Dict:
    """Evol-Instruct形式で指示を進化"""
    evolved = entry.copy()
    instruction = evolved.get("instruction", "")

    # ランダムに進化方法を選択
    evolution_type = random.choice(["depth", "breadth", "constraints"])

    if evolution_type == "depth":
        evolved["instruction"] = evolve_instruction_depth(instruction)
    elif evolution_type == "breadth":
        evolved["instruction"] = evolve_instruction_breadth(instruction)
    else:
        evolved["instruction"] = evolve_add_constraints(instruction)

    evolved["evolution_type"] = evolution_type
    evolved["generation"] = evolved.get("generation", 0) + 1

    return evolved

# ============================================================
# タイトル変形
# ============================================================

def transform_title(title: str) -> List[str]:
    """タイトルを変形して新しいバリエーションを生成"""
    transforms = []

    # 1. 疑問形への変換
    if not title.endswith("？") and not title.endswith("?"):
        question_version = re.sub(r"(.+)した$", r"\1したって本当？", title)
        if question_version != title:
            transforms.append(question_version)

    # 2. 括弧の追加/削除
    if "【" in title:
        no_bracket = re.sub(r"【.*?】", "", title).strip()
        if len(no_bracket) > 5:
            transforms.append(no_bracket)
    else:
        categories = ["保存版", "完全ガイド", "初心者向け", "2026年版"]
        bracket_version = f"【{random.choice(categories)}】{title}"
        transforms.append(bracket_version)

    # 3. 数字の追加
    if not re.search(r'\d', title):
        num_version = f"{random.choice(['3', '5', '7'])}つの理由：{title}"
        transforms.append(num_version)

    # 4. ネガティブ変換
    positive_words = ["した", "できた", "成功", "達成"]
    negative_words = ["しなかった", "やめた", "失敗から学んだ", "見直した"]

    for pos, neg in zip(positive_words, negative_words):
        if pos in title:
            neg_version = title.replace(pos, neg)
            transforms.append(neg_version)
            break

    return transforms

# ============================================================
# メイン処理
# ============================================================

def augment_data():
    """データ拡張を実行"""
    AUGMENTED_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        print(f"❌ 入力ファイルが見つかりません: {INPUT_FILE}")
        print("先に prepare_training_data_v2.py を実行してください。")
        return

    print("=" * 60)
    print("🔄 合成データ生成開始")
    print("=" * 60)

    # 元データ読み込み
    original_data = []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                original_data.append(json.loads(line))
            except:
                pass

    print(f"📊 元データ: {len(original_data)}件")

    augmented_data = []
    evol_data = []

    # 1. テンプレートベース拡張
    print("\n📝 テンプレートベース拡張...")
    pattern_counts = {}
    for entry in original_data:
        patterns = entry.get("analysis", {}).get("patterns", [])
        for pattern in patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    for pattern, count in pattern_counts.items():
        # 各パターンに対して不足分を生成
        target = max(50, count * 2)  # 最低50件または2倍
        needed = target - count

        if needed > 0:
            variations = generate_template_variations(pattern, needed)
            for variation in variations:
                augmented_entry = {
                    "title": variation,
                    "category": "synthetic",
                    "power_score": 0.0,  # 合成データはスコアなし
                    "source": "template",
                    "pattern": pattern,
                }
                augmented_data.append(augmented_entry)

    print(f"  → テンプレート生成: {len(augmented_data)}件")

    # 2. タイトル変形
    print("\n🔀 タイトル変形...")
    transform_count = 0
    for entry in original_data:
        title = entry.get("title", "")
        transforms = transform_title(title)

        for trans in transforms:
            augmented_entry = {
                "title": trans,
                "category": entry.get("category", "unknown"),
                "power_score": 0.0,
                "source": "transform",
                "original_title": title,
            }
            augmented_data.append(augmented_entry)
            transform_count += 1

    print(f"  → 変形生成: {transform_count}件")

    # 3. Evol-Instruct進化
    print("\n🧬 Evol-Instruct進化...")

    # Evol-Instruct形式のデータがあれば読み込み
    evol_input = PROCESSED_DIR / "evol_instruct_data.jsonl"
    if evol_input.exists():
        with open(evol_input, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    # 各エントリを進化
                    for _ in range(2):  # 2世代進化
                        evolved = evolve_instruction(entry)
                        evol_data.append(evolved)
                        entry = evolved
                except:
                    pass

    print(f"  → Evol-Instruct: {len(evol_data)}件")

    # 重複除去
    seen_titles = set()
    unique_augmented = []
    for entry in augmented_data:
        title = entry.get("title", "")
        if title not in seen_titles:
            seen_titles.add(title)
            unique_augmented.append(entry)

    # 保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # 元データも含める
        for entry in original_data:
            entry["source"] = "original"
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # 拡張データ
        for entry in unique_augmented:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if evol_data:
        with open(EVOL_OUTPUT_FILE, "w", encoding="utf-8") as f:
            for entry in evol_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    total = len(original_data) + len(unique_augmented)

    print("\n" + "=" * 60)
    print("✅ 合成データ生成完了!")
    print(f"📊 合計: {total}件 ({len(original_data)}元データ + {len(unique_augmented)}拡張)")
    if evol_data:
        print(f"🧬 Evol-Instruct: {len(evol_data)}件")
    print(f"\n📁 出力:")
    print(f"  - {OUTPUT_FILE}")
    if evol_data:
        print(f"  - {EVOL_OUTPUT_FILE}")
    print("=" * 60)

# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":
    augment_data()
