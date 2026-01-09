"""
noteAI - 2026 World-Class Inference Script
==========================================

Unsloth + Qwen3-8B で学習したモデルを使用した推論スクリプト

推奨モデル:
    - Qwen3-8B: 16GB VRAM向け（日本語最強）
    - Qwen3-4B: 8GB VRAM向け（120B匹敵の性能）

使用方法:
    python inference_2026.py --model path/to/model --category "副業"
    python inference_2026.py --model path/to/model --interactive
"""

import argparse
import json
from pathlib import Path

import torch


def load_model_unsloth(model_path: str):
    """Unslothでモデルを読み込み"""
    from unsloth import FastLanguageModel

    print(f"Loading model: {model_path}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=512,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)

    return model, tokenizer


def load_model_transformers(model_path: str):
    """Transformersでモデルを読み込み（Unslothなし）"""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Loading model: {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto",
    )

    return model, tokenizer


def generate_title(
    model,
    tokenizer,
    category: str,
    temperature: float = 0.7,
    max_new_tokens: int = 64,
) -> str:
    """タイトルを生成"""

    # ChatML形式のプロンプト
    messages = [
        {
            "role": "system",
            "content": "あなたはnote.comの人気記事タイトルを生成する専門AIです。読者の興味を引く、クリックしたくなるタイトルを生成します。"
        },
        {
            "role": "user",
            "content": f"「{category}」に関する、読者を惹きつけるnote記事のタイトルを1つ生成してください。"
        },
    ]

    # トークナイズ
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(model.device)

    # 生成
    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id,
        )

    # デコード（生成部分のみ）
    generated = tokenizer.decode(
        outputs[0][inputs.shape[1]:],
        skip_special_tokens=True
    )

    # 最初の行のみ
    title = generated.strip().split("\n")[0]

    return title


def generate_multiple_titles(
    model,
    tokenizer,
    category: str,
    n: int = 5,
) -> list:
    """複数のタイトルバリエーションを生成"""
    titles = []
    for i in range(n):
        temp = 0.6 + (i * 0.1)  # 0.6, 0.7, 0.8, 0.9, 1.0
        title = generate_title(model, tokenizer, category, temperature=temp)
        titles.append(title)
    return titles


def interactive_mode(model, tokenizer):
    """インタラクティブモード"""
    print("\n" + "="*60)
    print("🎯 noteAI Interactive Mode")
    print("="*60)
    print("カテゴリを入力してタイトルを生成します。")
    print("'quit' または 'exit' で終了。")
    print("'multi' + カテゴリ で5つのバリエーションを生成。")
    print("="*60)

    while True:
        try:
            user_input = input("\n📝 カテゴリ: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("👋 終了します。")
                break

            # 複数生成モード
            if user_input.lower().startswith("multi "):
                category = user_input[6:].strip()
                print(f"\n【{category}】のタイトル候補:")
                print("-" * 40)
                titles = generate_multiple_titles(model, tokenizer, category)
                for i, title in enumerate(titles, 1):
                    print(f"  {i}. {title}")
            else:
                # 単一生成
                title = generate_title(model, tokenizer, user_input)
                print(f"\n✨ 生成タイトル: {title}")

        except KeyboardInterrupt:
            print("\n\n👋 終了します。")
            break


def main():
    parser = argparse.ArgumentParser(
        description="noteAI Title Generator - 2026 World-Class"
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="モデルのパス（LoRAアダプターまたはマージ済みモデル）"
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="タイトルを生成するカテゴリ"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="インタラクティブモードで起動"
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="生成するタイトルの数"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="生成温度（0.1-1.5）"
    )
    parser.add_argument(
        "--use-transformers",
        action="store_true",
        help="Unslothの代わりにTransformersを使用"
    )

    args = parser.parse_args()

    # モデル読み込み
    if args.use_transformers:
        model, tokenizer = load_model_transformers(args.model)
    else:
        try:
            model, tokenizer = load_model_unsloth(args.model)
        except ImportError:
            print("⚠️ Unslothがインストールされていません。Transformersを使用します。")
            model, tokenizer = load_model_transformers(args.model)

    print("✅ Model loaded!")

    # 実行モード
    if args.interactive:
        interactive_mode(model, tokenizer)
    elif args.category:
        if args.n > 1:
            print(f"\n【{args.category}】のタイトル候補:")
            print("-" * 40)
            titles = generate_multiple_titles(model, tokenizer, args.category, n=args.n)
            for i, title in enumerate(titles, 1):
                print(f"  {i}. {title}")
        else:
            title = generate_title(
                model, tokenizer, args.category,
                temperature=args.temperature
            )
            print(f"\n✨ 生成タイトル: {title}")
    else:
        print("エラー: --category または --interactive を指定してください")
        parser.print_help()


if __name__ == "__main__":
    main()
