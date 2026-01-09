"""
noteAI データ準備スクリプト v2.0
2026年世界最高水準版

改善点:
- Evol-Instruct形式対応
- 多次元品質評価
- タイトル特徴抽出強化
- 難易度ラベル付け
"""

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# 設定
# ============================================================

DATA_DIR = Path("data")
RAW_DATA_FILE = DATA_DIR / "raw_notes_custom.jsonl"  # 収集済みデータ
OUTPUT_DIR = DATA_DIR / "processed"

# 出力ファイル
TRAINING_FILE = OUTPUT_DIR / "training_data_v2.jsonl"
EVOL_INSTRUCT_FILE = OUTPUT_DIR / "evol_instruct_data.jsonl"
QUALITY_REPORT_FILE = OUTPUT_DIR / "quality_report.json"

# 品質フィルタ設定
QUALITY_CONFIG = {
    "min_title_length": 5,
    "max_title_length": 100,
    "min_power_score": 1.0,      # 成功例の閾値
    "min_virality_score": 50,    # バイラル閾値
    "exclude_patterns": [
        r"^\d+$",                 # 数字のみ
        r"^【.*】$",              # 記号のみ
        r"^第\d+話",              # 連載タイトル
        r"^#\d+",                 # ナンバリング
    ],
}

# タイトルパターン分類
TITLE_PATTERNS = {
    "question": r"[？\?]$|^なぜ|^どうして|^どう|とは\？",
    "number_list": r"^\d+つ|^\d+選|^\d+個|TOP\d+|\d+つの",
    "how_to": r"^〜の方法|する方法|のやり方|の始め方|のコツ",
    "experience": r"してみた|やってみた|を試した|体験記",
    "confession": r"した話|という話|って話|の話$",
    "contrast": r"と|vs|より|じゃなくて",
    "negative": r"^やめた|辞めた|しない|捨てた|やらない",
    "transformation": r"から|になった|に変わった|できるように",
    "emotional": r"[！!]{2,}|本当に|マジで|ガチで|めちゃくちゃ",
    "quotation": r"^「|^『|」$|』$",
}

# ============================================================
# タイトル分析
# ============================================================

@dataclass
class TitleAnalysis:
    """タイトルの分析結果"""
    title: str
    length: int
    char_types: Dict[str, int]  # ひらがな、カタカナ、漢字、数字、記号
    patterns: List[str]         # 検出されたパターン
    hooks: List[str]            # フック要素
    difficulty: str             # easy, medium, hard
    quality_score: float        # 品質スコア（0-1）

def analyze_char_types(text: str) -> Dict[str, int]:
    """文字種別をカウント"""
    types = {
        "hiragana": 0,
        "katakana": 0,
        "kanji": 0,
        "number": 0,
        "symbol": 0,
        "alphabet": 0,
    }

    for char in text:
        if '\u3040' <= char <= '\u309F':
            types["hiragana"] += 1
        elif '\u30A0' <= char <= '\u30FF':
            types["katakana"] += 1
        elif '\u4E00' <= char <= '\u9FFF':
            types["kanji"] += 1
        elif char.isdigit():
            types["number"] += 1
        elif char.isalpha():
            types["alphabet"] += 1
        else:
            types["symbol"] += 1

    return types

def detect_patterns(title: str) -> List[str]:
    """タイトルパターンを検出"""
    detected = []
    for pattern_name, pattern_regex in TITLE_PATTERNS.items():
        if re.search(pattern_regex, title):
            detected.append(pattern_name)
    return detected

def detect_hooks(title: str) -> List[str]:
    """フック要素を検出"""
    hooks = []

    # 数字の使用
    if re.search(r'\d+', title):
        hooks.append("uses_numbers")

    # 括弧・記号の使用
    if re.search(r'【|】|「|」|『|』', title):
        hooks.append("uses_brackets")

    # 感情的な表現
    emotional_words = ["本当に", "マジで", "ガチで", "めちゃくちゃ", "超", "最強", "神"]
    for word in emotional_words:
        if word in title:
            hooks.append("emotional_language")
            break

    # ネガティブフック
    negative_words = ["やめた", "辞めた", "しない", "捨てた", "やらない", "失敗"]
    for word in negative_words:
        if word in title:
            hooks.append("negative_hook")
            break

    # 変化・結果を示唆
    if re.search(r"になった|できた|変わった|達成", title):
        hooks.append("shows_transformation")

    # 限定性
    if re.search(r"だけ|のみ|限定|秘密", title):
        hooks.append("exclusivity")

    return list(set(hooks))

def calculate_quality_score(title: str, patterns: List[str], hooks: List[str],
                           char_types: Dict[str, int]) -> float:
    """タイトルの品質スコアを計算"""
    score = 0.5  # 基準点

    # 長さボーナス（15-40文字が最適）
    length = len(title)
    if 15 <= length <= 40:
        score += 0.1
    elif length < 10 or length > 60:
        score -= 0.1

    # パターンボーナス
    score += min(len(patterns) * 0.05, 0.15)

    # フックボーナス
    score += min(len(hooks) * 0.05, 0.2)

    # 文字種バランス（漢字+ひらがなのバランス）
    total_chars = sum(char_types.values())
    if total_chars > 0:
        kanji_ratio = char_types["kanji"] / total_chars
        if 0.2 <= kanji_ratio <= 0.5:
            score += 0.05

    return min(max(score, 0.0), 1.0)

def determine_difficulty(title: str, patterns: List[str], power_score: float) -> str:
    """難易度を判定"""
    complexity = 0

    # パターン数による複雑さ
    complexity += len(patterns)

    # 長さによる複雑さ
    if len(title) > 30:
        complexity += 1
    if len(title) > 50:
        complexity += 1

    # Power Scoreによる難易度
    if power_score >= 3.0:
        complexity += 2  # 非常に成功したタイトルは再現が難しい

    if complexity <= 2:
        return "easy"
    elif complexity <= 4:
        return "medium"
    else:
        return "hard"

def analyze_title(title: str, power_score: float = 0.0) -> TitleAnalysis:
    """タイトルを総合分析"""
    char_types = analyze_char_types(title)
    patterns = detect_patterns(title)
    hooks = detect_hooks(title)
    quality_score = calculate_quality_score(title, patterns, hooks, char_types)
    difficulty = determine_difficulty(title, patterns, power_score)

    return TitleAnalysis(
        title=title,
        length=len(title),
        char_types=char_types,
        patterns=patterns,
        hooks=hooks,
        difficulty=difficulty,
        quality_score=quality_score,
    )

# ============================================================
# Evol-Instruct形式生成
# ============================================================

def create_instruction_variants(title: str, analysis: TitleAnalysis,
                                category: str, power_score: float) -> List[Dict]:
    """Evol-Instruct形式の指示バリエーションを生成"""
    variants = []

    # 基本形式
    base_instruction = {
        "instruction": f"以下のテーマに関する、読者を惹きつけるnote記事のタイトルを考えてください。\nテーマ: {category}",
        "input": "",
        "output": title,
        "metadata": {
            "power_score": power_score,
            "patterns": analysis.patterns,
            "hooks": analysis.hooks,
            "difficulty": analysis.difficulty,
            "quality_score": analysis.quality_score,
        }
    }
    variants.append(base_instruction)

    # パターン指定形式
    if analysis.patterns:
        pattern_names = {
            "question": "疑問形",
            "number_list": "数字リスト",
            "how_to": "ハウツー",
            "experience": "体験談",
            "confession": "告白系",
            "negative": "ネガティブフック",
            "transformation": "変化・成長",
            "emotional": "感情的",
        }
        pattern_desc = "・".join([pattern_names.get(p, p) for p in analysis.patterns[:2]])

        pattern_instruction = {
            "instruction": f"「{pattern_desc}」のパターンを使った、バズるnote記事のタイトルを作成してください。",
            "input": f"カテゴリ: {category}",
            "output": title,
            "metadata": base_instruction["metadata"],
        }
        variants.append(pattern_instruction)

    # 難易度別形式（medium以上のみ）
    if analysis.difficulty in ["medium", "hard"]:
        advanced_instruction = {
            "instruction": "高いエンゲージメントを獲得した実績のあるタイトルパターンを参考に、同様の効果が期待できるタイトルを生成してください。",
            "input": f"分野: {category}\n成功パターン: {', '.join(analysis.patterns)}\nフック要素: {', '.join(analysis.hooks)}",
            "output": title,
            "metadata": base_instruction["metadata"],
        }
        variants.append(advanced_instruction)

    return variants

# ============================================================
# データ処理
# ============================================================

def should_include(note: Dict) -> bool:
    """記事を含めるべきか判定"""
    title = note.get("title", "")

    # 長さチェック
    if len(title) < QUALITY_CONFIG["min_title_length"]:
        return False
    if len(title) > QUALITY_CONFIG["max_title_length"]:
        return False

    # 除外パターンチェック
    for pattern in QUALITY_CONFIG["exclude_patterns"]:
        if re.match(pattern, title):
            return False

    return True

def process_data():
    """データを処理してEvol-Instruct形式に変換"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW_DATA_FILE.exists():
        print(f"❌ データファイルが見つかりません: {RAW_DATA_FILE}")
        return

    print("=" * 60)
    print("🔄 データ準備 v2.0 開始")
    print("=" * 60)

    # 統計情報
    stats = {
        "total_raw": 0,
        "filtered_out": 0,
        "success_examples": 0,
        "evol_instruct_count": 0,
        "categories": Counter(),
        "patterns": Counter(),
        "difficulties": Counter(),
    }

    training_data = []
    evol_instruct_data = []

    # データ読み込み
    with open(RAW_DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                note = json.loads(line)
                stats["total_raw"] += 1

                # フィルタリング
                if not should_include(note):
                    stats["filtered_out"] += 1
                    continue

                title = note["title"]
                power_score = note.get("power_score", 0)
                category = note.get("category", "unknown")

                # タイトル分析
                analysis = analyze_title(title, power_score)

                # 統計更新
                stats["categories"][category] += 1
                for pattern in analysis.patterns:
                    stats["patterns"][pattern] += 1
                stats["difficulties"][analysis.difficulty] += 1

                # 成功例判定（Power Score >= 1.0）
                if power_score >= QUALITY_CONFIG["min_power_score"]:
                    stats["success_examples"] += 1

                    # 基本トレーニングデータ
                    training_entry = {
                        "title": title,
                        "category": category,
                        "power_score": power_score,
                        "virality_score": note.get("virality_score", 0),
                        "analysis": asdict(analysis),
                        "user_nickname": note.get("user_nickname", ""),
                        "follower_count": note.get("follower_count", 0),
                        "like_count": note.get("like_count", 0),
                    }
                    training_data.append(training_entry)

                    # Evol-Instruct形式
                    variants = create_instruction_variants(
                        title, analysis, category, power_score
                    )
                    for variant in variants:
                        evol_instruct_data.append(variant)
                        stats["evol_instruct_count"] += 1

            except Exception as e:
                print(f"  ⚠️ エラー: {e}")
                continue

    # データ保存
    with open(TRAINING_FILE, "w", encoding="utf-8") as f:
        for entry in training_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with open(EVOL_INSTRUCT_FILE, "w", encoding="utf-8") as f:
        for entry in evol_instruct_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 品質レポート
    report = {
        "summary": {
            "total_raw": stats["total_raw"],
            "filtered_out": stats["filtered_out"],
            "success_examples": stats["success_examples"],
            "evol_instruct_count": stats["evol_instruct_count"],
        },
        "categories": dict(stats["categories"].most_common()),
        "patterns": dict(stats["patterns"].most_common()),
        "difficulties": dict(stats["difficulties"]),
    }

    with open(QUALITY_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 結果表示
    print(f"\n📊 処理結果:")
    print(f"  - 生データ: {stats['total_raw']}件")
    print(f"  - フィルタ除外: {stats['filtered_out']}件")
    print(f"  - 成功例: {stats['success_examples']}件")
    print(f"  - Evol-Instruct形式: {stats['evol_instruct_count']}件")

    print(f"\n📁 出力ファイル:")
    print(f"  - {TRAINING_FILE}")
    print(f"  - {EVOL_INSTRUCT_FILE}")
    print(f"  - {QUALITY_REPORT_FILE}")

    print("\n" + "=" * 60)
    print("✅ データ準備完了!")
    print("=" * 60)

# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":
    process_data()
