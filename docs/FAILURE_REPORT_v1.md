# noteAI v1 失敗レポート

**作成日**: 2026年1月9日
**ステータス**: ❌ 失敗（モデルがゴミ出力を生成）

---

## 1. プロジェクト概要

| 項目 | 内容 |
|------|------|
| **目的** | note.comの人気記事タイトルを自動生成するAI |
| **ベースモデル** | `unsloth/Qwen3-14B-bnb-4bit` (14.9Bパラメータ) |
| **トレーニング環境** | Google Colab (A100 40GB) |
| **推論環境** | ローカル Windows (RTX 5060 Ti 16GB, i9-7980XE, 128GB RAM) |
| **推論ツール** | llama.cpp b7681 Windows CUDA 12.4 |

---

## 2. 失敗の症状

### 2.1 観察された出力

**入力プロンプト（ChatML形式）**:
```
<|im_start|>system
あなたはnote.comの人気記事タイトルを生成する専門AIです。
<|im_end|>
<|im_start|>user
「副業」に関する記事タイトルを1つ生成してください。
<|im_end|>
<|im_start|>assistant
```

**Q4_K_M版の出力**:
```
⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉...
```

**F16版の出力**:
```
「副業」」」」」」」」」」」」」」」」」」」」」」」」」」」」」」」」」...
```

### 2.2 重要な発見

| 検証 | 結果 | 意味 |
|------|------|------|
| Q4_K_M版テスト | ❌ ゴミ出力 | - |
| **F16版テスト** | ❌ ゴミ出力 | **量子化の問題ではない** |
| **結論** | トレーニング自体が失敗 | データ/ハイパーパラメータの問題 |

---

## 3. トレーニング設定（使用した値）

### 3.1 LoRA設定
```python
model = FastLanguageModel.get_peft_model(
    model,
    r=32,                    # LoRAランク
    lora_alpha=64,           # alpha = 2 * r（rsLoRA推奨値）
    lora_dropout=0.0,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    use_rslora=True,         # rsLoRA有効
    use_gradient_checkpointing="unsloth",
)
```

### 3.2 トレーニング設定
```python
training_args = SFTConfig(
    output_dir="./outputs",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-4,
    warmup_ratio=0.1,
    lr_scheduler_type="cosine",
    logging_steps=10,
    save_steps=100,
    bf16=True,
    optim="adamw_8bit",
    seed=42,
    max_seq_length=512,
)
```

### 3.3 トレーニング結果
| メトリクス | 値 |
|------------|-----|
| 初期Loss | 2.847 |
| 最終Loss | 0.254 |
| Loss減少率 | 91% |
| エポック | 3 |
| 総ステップ | 約240 |

**警告サイン**: Lossが0.254まで下がったのは**オーバーフィットの可能性**を示唆

---

## 4. データ品質分析

### 4.1 データ統計

| ファイル | 総数 | 問題データ | 汚染率 |
|----------|------|------------|--------|
| `raw_notes_custom.jsonl` | 657 | 142（タグ形式） | **22%** |
| `evol_instruct_data.jsonl` | 638 | 180（タグ形式） | **28%** |

### 4.2 問題データの例

**❌ 悪い例（タグ形式 - ゴミデータ）**:
```
自己紹介｜子育て｜ワーママ｜30代｜40代｜50代｜...
```

**✅ 良い例（実際のタイトル）**:
```
【就職倍率100倍の公務員を辞めた】安定を捨てた20代の挫折と好転
```

### 4.3 重複の問題
- 「主婦が積立NISA...」のようなタイトルが3回以上重複
- 重複はオーバーフィットを悪化させる

---

## 5. 根本原因分析

### 5.1 確定した原因

| 原因 | 説明 | 重要度 |
|------|------|--------|
| **データ品質** | 28%がタグ形式ゴミデータ | ⭐⭐⭐ 最重要 |
| **データ量不足** | 638サンプル（推奨: 1,000+） | ⭐⭐ 重要 |
| **オーバーフィット** | 小規模データ × 3エポック × 低Loss | ⭐⭐ 重要 |
| **重複データ** | 同じタイトルが複数回出現 | ⭐ 中程度 |

### 5.2 オンライン調査からの証拠

**Reddit r/LocalLLaMA（2024年4月）**:
> "50 epochs is 100% overfitting. 10x your data count and train for Max 5 epochs"
> - 状況: 250 Q&A、50エポック、Loss 0.37 → ゴミ出力
> - **あなたのケースと酷似**: 638サンプル、3エポック、Loss 0.254

**GitHub Unsloth #2860（2025年7月）**:
> Qwen3 4bitのGGUF変換でNaN値が発生し「GGGG...」出力
> - 解決策: FP16/BF16でトレーニング → 最新Unslothで変換
> - **あなたのケース**: F16でもゴミ出力 → 変換ではなくトレーニングの問題

**HuggingFace Forum SFT Collapse議論**:
> "800 samples is far too little to robustly bake in CoT behavior"
> "Instruct model expects specific chat template - if you fine-tune without matching it, collapse occurs"

**SuperAnnotate Best Practices Guide**:
> "Minimum 1,000 samples recommended for robust fine-tuning"
> "Data quality accounts for 80% of fine-tuning success"

---

## 6. 技術的詳細

### 6.1 生成されたファイル

| ファイル | サイズ | 状態 |
|----------|--------|------|
| `noteai-qwen3-14b-title-v1-f16.gguf` | 27.51 GB | ❌ ゴミ出力 |
| `noteai-qwen3-14b-title-v1-Q4_K_M.gguf` | 8.38 GB | ❌ ゴミ出力 |

### 6.2 推論テスト環境
```
llama.cpp build: b7681
CUDA: 12.4
GPU: RTX 5060 Ti (16GB VRAM)
-ngl: 20（GPU層数）
```

### 6.3 推論速度
```
Prompt: 39.9 t/s
Generation: 2.0 t/s（F16版、GPU層20）
```

---

## 7. 学んだ教訓

### 7.1 データに関する教訓

1. **「Data is king - 80% of your time should be on data preparation」**
   - データ収集前にフィルタリング基準を定義すべきだった
   - タグ形式 vs タイトル形式の区別が不十分だった

2. **データ量の目安**
   - 最低: 1,000サンプル
   - 推奨: 5,000+サンプル
   - 現実: 638サンプル（不足）

3. **重複チェックは必須**
   - トレーニング前に重複除去を行うべき

### 7.2 トレーニングに関する教訓

1. **エポック数**
   - 小規模データでは1-2エポックが適切
   - 3エポック以上はオーバーフィットのリスク大

2. **Lossの解釈**
   - 低いLoss（< 0.5）は必ずしも良いわけではない
   - 急激なLoss低下はオーバーフィットの兆候

3. **検証セットの重要性**
   - 検証セットなしでトレーニングすると品質評価が困難
   - 10-20%を検証用に分割すべき

### 7.3 変換・推論に関する教訓

1. **GGUF変換前に必ずPyTorchで検証**
   - `model.generate()`で正常出力を確認してから変換

2. **段階的検証**
   - LoRAアダプター → マージ済みモデル → F16 GGUF → 量子化GGUF
   - 各段階で推論テストを実施

---

## 8. 修正計画

### Phase 1: データクリーニング
1. タグ形式エントリを除去（`｜`で区切られた単語羅列）
2. 重複タイトルを除去
3. 残りのクリーンなデータ数を確認
4. 必要に応じてデータ拡張

### Phase 2: データ拡張（必要な場合）
1. Evol-Instructパターンの多様化
2. 追加のnote.com記事収集
3. 合成データ生成の検討

### Phase 3: 再トレーニング
1. エポック数を1-2に削減
2. 検証セット（10%）を分割
3. Early stoppingの導入を検討

### Phase 4: 段階的検証
1. PyTorchで推論テスト
2. F16 GGUFで推論テスト
3. Q4_K_M GGUFで推論テスト

---

## 9. 参考リンク

- [Reddit: Got garbage response after fine-tuning](https://www.reddit.com/r/LocalLLaMA/comments/1caeisk/got_garbage_response_after_finetuning/)
- [GitHub: Unsloth #2860 - Qwen3 GGUF Conversion Bug](https://github.com/unslothai/unsloth/issues/2860)
- [Reddit: A comprehensive overview of fine-tuning](https://www.reddit.com/r/LocalLLaMA/comments/1ilkamr/a_comprehensive_overview_of_everything_i_know/)
- [SuperAnnotate: LLM Fine-tuning Best Practices](https://www.superannotate.com/blog/llm-fine-tuning-best-practices)

---

## 10. 付録: 失敗時のログ

### 10.1 Q4_K_M版テスト
```
llama-cli -m "noteai-qwen3-14b-title-v1-Q4_K_M.gguf" -ngl 99 -p "..."
出力: ⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉⌉...
速度: Prompt 35.1 t/s, Generation 5.8 t/s
```

### 10.2 F16版テスト
```
llama-cli -m "noteai-qwen3-14b-title-v1-f16.gguf" -ngl 20 -p "..."
出力: 「副業」」」」」」」」」」」」」」」」」」」」」」」」」」」」」」」」」...
速度: Prompt 39.9 t/s, Generation 2.0 t/s
```

---

**このレポートは将来の参照用に保存されています。**
**次のバージョン（v2）では上記の修正計画を実施します。**
