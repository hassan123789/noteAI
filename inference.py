"""
note.com タイトルAI 推論スクリプト
====================================
学習済みモデルを使ってタイトルを生成・評価するスクリプト

使い方:
  python inference.py --keyword "副業"
  python inference.py --keyword "AI" --num 10
  python inference.py --interactive
"""

import argparse
import json
import re
from pathlib import Path

# ============================================================
# 設定
# ============================================================
# 学習済みモデルがない場合はルールベースで動作
TRAINING_DATA = "generation_training.jsonl"


# ============================================================
# タイトル特徴分析（ルールベース）
# ============================================================
class TitleAnalyzer:
    """成功タイトルの特徴を分析"""

    def __init__(self, training_file: str = TRAINING_DATA):
        self.patterns = self._load_patterns(training_file)

    def _load_patterns(self, filepath: str) -> dict:
        """学習データからパターンを抽出"""
        patterns = {
            "brackets": [],  # 【】の使い方
            "numbers": [],  # 数字の使い方
            "keywords": [],  # 頻出キーワード
            "structures": [],  # 文構造パターン
            "lengths": [],  # 文字数分布
        }

        if not Path(filepath).exists():
            return patterns

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                title = data["output"]
                patterns["lengths"].append(len(title))

                # 【】パターン抽出
                bracket_match = re.findall(r"【(.+?)】", title)
                patterns["brackets"].extend(bracket_match)

                # 数字パターン
                number_match = re.findall(
                    r"\d+(?:万|円|%|人|分|日|ヶ月|年|つ|個)?", title
                )
                patterns["numbers"].extend(number_match)

                # キーワード
                keywords = [
                    "副業",
                    "稼ぐ",
                    "収益",
                    "AI",
                    "簡単",
                    "無料",
                    "方法",
                    "やってみた",
                    "始め",
                    "挑戦",
                    "完全",
                    "攻略",
                    "秘密",
                ]
                for kw in keywords:
                    if kw in title:
                        patterns["keywords"].append(kw)

        return patterns

    def analyze(self, title: str) -> dict:
        """タイトルのスコアリング"""
        score = 0.0
        factors = []

        # 文字数チェック (30-60文字が理想)
        length = len(title)
        if 30 <= length <= 60:
            score += 1.0
            factors.append(f"✓ 文字数適正 ({length}文字)")
        elif length < 20:
            score -= 0.5
            factors.append(f"✗ 短すぎ ({length}文字)")
        elif length > 80:
            score -= 0.5
            factors.append(f"✗ 長すぎ ({length}文字)")

        # 【】括弧の使用
        if re.search(r"【.+?】", title):
            score += 1.5
            factors.append("✓ 【】括弧でアイキャッチ")

        # 数字の使用
        if re.search(r"\d+", title):
            score += 1.0
            factors.append("✓ 数字で具体性")

        # パワーワード
        power_words = ["完全", "最強", "攻略", "秘密", "真実", "本当", "衝撃", "驚き"]
        for pw in power_words:
            if pw in title:
                score += 0.5
                factors.append(f"✓ パワーワード: {pw}")
                break

        # 金銭関連
        if re.search(r"(稼|万円|収益|月収|副業|収入)", title):
            score += 1.0
            factors.append("✓ 収益関連ワード")

        # アクション喚起
        if re.search(r"(やってみた|してみた|試した|始め|挑戦|方法|やり方)", title):
            score += 0.5
            factors.append("✓ アクション喚起")

        # ネガティブファクター
        if re.search(r"(自己紹介|はじめて|サイトマップ)", title):
            score -= 2.0
            factors.append("✗ 一般的すぎるタイトル")

        return {
            "score": round(score, 2),
            "grade": self._score_to_grade(score),
            "factors": factors,
        }

    def _score_to_grade(self, score: float) -> str:
        if score >= 4.0:
            return "S (優秀)"
        elif score >= 3.0:
            return "A (良好)"
        elif score >= 2.0:
            return "B (標準)"
        elif score >= 1.0:
            return "C (改善余地あり)"
        else:
            return "D (要改善)"


# ============================================================
# タイトル生成（テンプレートベース）
# ============================================================
class TitleGenerator:
    """成功パターンに基づくタイトル生成"""

    TEMPLATES = [
        "【{keyword}】{benefit}するための{method}",
        "【完全版】{keyword}で{goal}を達成する方法",
        "【{year}年最新】{keyword}の{method}を徹底解説",
        "{keyword}で月{amount}円稼ぐ{adjective}な方法",
        "【悪用厳禁】{keyword}を{period}で{goal}する裏技",
        "「{problem}」を解決！{keyword}の{solution}",
        "【初心者向け】{keyword}の始め方完全ガイド",
        "{number}%の人が知らない{keyword}の{secret}",
        "【体験談】{keyword}を{period}やってみた結果",
        "{keyword}で{goal}できた{adjective}すぎる方法",
    ]

    FILLS = {
        "benefit": ["収益化", "効率化", "自動化", "最適化", "成功"],
        "method": ["完全攻略法", "実践テクニック", "成功の秘訣", "具体的手順"],
        "goal": ["月5万円", "月10万円", "収益", "成果", "結果"],
        "year": ["2024", "2025"],
        "amount": ["5万", "10万", "20万", "50万"],
        "adjective": ["簡単", "確実", "シンプル", "驚き", "意外"],
        "period": ["30日", "1ヶ月", "3ヶ月", "半年"],
        "problem": ["時間がない", "続かない", "わからない", "稼げない"],
        "solution": ["解決策", "対処法", "突破口", "攻略法"],
        "number": ["90", "95", "80", "99"],
        "secret": ["秘密", "真実", "裏側", "本質"],
    }

    def generate(self, keyword: str, num: int = 5) -> list:
        """キーワードからタイトル候補を生成"""
        import random

        titles = []
        templates = random.sample(self.TEMPLATES, min(num, len(self.TEMPLATES)))

        for template in templates:
            title = template
            title = title.replace("{keyword}", keyword)

            # 他のプレースホルダーを埋める
            for key, values in self.FILLS.items():
                placeholder = "{" + key + "}"
                if placeholder in title:
                    title = title.replace(placeholder, random.choice(values))

            titles.append(title)

        return titles


# ============================================================
# メイン処理
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="note.com タイトルAI")
    parser.add_argument("--keyword", "-k", type=str, help="タイトル生成のキーワード")
    parser.add_argument("--num", "-n", type=int, default=5, help="生成数")
    parser.add_argument("--analyze", "-a", type=str, help="タイトルを分析")
    parser.add_argument("--interactive", "-i", action="store_true", help="対話モード")

    args = parser.parse_args()

    analyzer = TitleAnalyzer()
    generator = TitleGenerator()

    if args.analyze:
        # 分析モード
        print("=" * 60)
        print("タイトル分析")
        print("=" * 60)
        print(f"\nタイトル: {args.analyze}")
        result = analyzer.analyze(args.analyze)
        print(f"\nスコア: {result['score']} → {result['grade']}")
        print("\n評価要因:")
        for factor in result["factors"]:
            print(f"  {factor}")

    elif args.keyword:
        # 生成モード
        print("=" * 60)
        print(f"「{args.keyword}」のタイトル候補")
        print("=" * 60)

        titles = generator.generate(args.keyword, args.num)
        for i, title in enumerate(titles, 1):
            result = analyzer.analyze(title)
            print(f"\n{i}. {title}")
            print(f"   [{result['grade']}] スコア: {result['score']}")

    elif args.interactive:
        # 対話モード
        print("=" * 60)
        print("note.com タイトルAI - 対話モード")
        print("=" * 60)
        print("\nコマンド:")
        print("  gen <キーワード>  - タイトル生成")
        print("  ana <タイトル>    - タイトル分析")
        print("  quit              - 終了")

        while True:
            try:
                cmd = input("\n> ").strip()
                if not cmd:
                    continue

                if cmd.lower() == "quit":
                    print("終了します")
                    break

                if cmd.startswith("gen "):
                    keyword = cmd[4:].strip()
                    print(f"\n【{keyword}】のタイトル候補:")
                    for i, title in enumerate(generator.generate(keyword), 1):
                        result = analyzer.analyze(title)
                        print(f"  {i}. [{result['grade']}] {title}")

                elif cmd.startswith("ana "):
                    title = cmd[4:].strip()
                    result = analyzer.analyze(title)
                    print(f"\nスコア: {result['score']} → {result['grade']}")
                    for factor in result["factors"]:
                        print(f"  {factor}")

                else:
                    print("不明なコマンドです。gen/ana/quit を使用してください。")

            except KeyboardInterrupt:
                print("\n終了します")
                break

    else:
        # ヘルプ表示
        parser.print_help()


if __name__ == "__main__":
    main()
