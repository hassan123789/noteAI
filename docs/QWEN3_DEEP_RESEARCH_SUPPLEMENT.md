# Qwen3 深層リサーチ補足ドキュメント

> WORLD_CLASS_FINETUNING_STANDARDS.md の補足資料
>
> **作成日**: 2025年1月
> **目的**: 徹底的なWebリサーチで発見したQwen3特有の問題と対策

---

## 🚨 セクション1: Qwen3特有の問題と対策（超重要）

### Qwen Tokenizerの特殊性

**ソース**: Qwen公式ドキュメント（qwen.readthedocs.io）

| トークン | 役割 | 注意点 |
|----------|------|--------|
| `<\|im_start\|>` | ターン開始（bot token） | 各ターンの先頭に必須 |
| `<\|im_end\|>` | ターン終了（eot token） | **これがEOS扱い** |
| `<\|endoftext\|>` | ドキュメント終了（eod token） | 会話終了時に追加される |

### ⚠️ 超重要: Qwenのeos_token問題

Qwen公式ドキュメントより:
> "Qwen does not append a fixed token to each packed training sequence. However, as most frameworks do not have the concept of eot and use eos instead for stopping criteria in inference, **eos token is set to eot for Qwen**."

**つまり**:

- Qwenはデフォルトで `eos_token` を持たない
- しかし推論フレームワークは `eos_token` で停止判定
- Qwenでは `<|im_end|>` が `eos_token` として使われる
- ファインチューニングでこの設定が壊れると**無限生成**や**ゴミ出力**

### ChatML形式（Qwen必須フォーマット）

```
<|im_start|>system
{システムプロンプト}<|im_end|>
<|im_start|>user
{ユーザー入力}<|im_end|>
<|im_start|>assistant
{モデル出力}<|im_end|>
```

**Qwen3からの変更点**:

- デフォルトシステムプロンプトが削除された
- 151,646トークンの大規模ボキャブラリー

### 既知のQwen3問題（GitHub Issues調査結果）

| Issue | 問題 | 原因 | 対策 |
|-------|------|------|------|
| **llama.cpp #13310** | Qwen3が"GGGGG..."ゴミ出力 | トークナイザーミスマッチ、プロンプトテンプレート | 正確なChatMLフォーマット使用 |
| **Axolotl #2073** | ファインチューニング後に`<\|im_end\|>`を生成できない → ゴミ出力 | EOS設定不備 | tokenizer設定を明示的に確認 |
| **Unsloth #2405** | 長い入力でゴミ出力 | コンテキスト超過 | max_seq_length調整 |
| **Unsloth #1333** | Qwen 2.5でtrain_on_responses_onlyエラー | Triton AssertionError | Unslothバージョン確認 |

### Axolotl #2073 の詳細（noteAI失敗と類似）

報告内容:
> "Qwen 2.5 Base unable to generate `<|im_end|>` even after finetuning"
> "Model generates answer then gibberish: 'The answer is: 11 prostituerade...11VRTX...'"

**これはnoteAI v1の症状と酷似！**

- 回答を出力後にゴミ文字
- `<|im_end|>`を生成できない = 停止できない

### Unsloth train_on_responses_only設定（Qwen用）

**正確な設定**:

```python
from unsloth.chat_templates import train_on_responses_only

trainer = train_on_responses_only(
    trainer,
    instruction_part = "<|im_start|>user\n",
    response_part = "<|im_start|>assistant\n",
)
```

⚠️ **改行の位置に注意**！`\n`の有無で動作が変わる

HuggingFace Spaceで事前テスト可能:

- train_on_responses_only機能をテストするSpaceが存在
- モデルIDを入力して正しく動作するか確認可能

### Qwen専用チェックリスト

- [ ] `eos_token` が `<|im_end|>` に設定されているか
- [ ] 訓練データに `<|im_end|>` が正しく含まれているか
- [ ] ChatMLフォーマットが正確に守られているか
- [ ] `train_on_responses_only` の区切り文字が正しいか
- [ ] `max_seq_length` が適切か（長すぎる入力でゴミ出力）
- [ ] Qwen3のデフォルトシステムプロンプト削除を考慮しているか

---

## 📊 セクション2: LoRA Rank/Alpha の深い理解

### Alpha/Rank 比率の真実

**ソース**: Reddit r/LocalLLaMA、DataScience StackExchange、Thinking Machines Blog

| 設定 | 効果 | 推奨 |
|------|------|------|
| alpha = rank | 標準的なスケーリング | ✅ 推奨 |
| alpha < rank | ファインチューニング効果が**強まる** | 注意必要 |
| alpha > rank | ファインチューニング効果が**弱まる** | 場合による |
| alpha = 16（固定） | 元のLoRA論文の推奨 | 保守的 |

Reddit r/LocalLLaMaより:
> "Decreasing alpha relative to rank increases the effect of fine-tuning. Increasing alpha relative to rank decreases it."

DataScience StackExchangeより:
> "Alpha scales the learned weights. Existing literature, including the original LoRA paper, generally advises fixing Alpha—often at 16—rather than tuning it."

### LoRA Without Regret（最新研究 2025）

**ソース**: Thinking Machines Lab Blog

> "LoRA can match Full Fine-Tuning when you set it up correctly"

重要な発見:

1. **LoRAの最適LRはFull FTの10倍**
2. **rank > 256は効果薄**（容量制約がなくなる）
3. **MLP/MoEブロックにアダプタ配置で最大効果**
4. **強化学習ではrank=1でもFull FTと同等**
5. **LoRAは小〜中規模ポストトレーニングデータセットで最も効果的**

### noteAI向けLoRA設定（最終推奨）

```python
lora_config = {
    "r": 32,           # rank（問題なし）
    "lora_alpha": 64,  # alpha = rank × 2（問題なし）
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
    "lora_dropout": 0.0,  # 小規模データでは0.05も検討
    "use_rslora": True,   # rsLoRA推奨
}
```

**結論**: noteAI v1のLoRA設定自体は適正。問題はデータ品質とEOS設定。

---

## 🔄 セクション3: GGUF変換の落とし穴

### 既知の問題（GitHub Issues収集）

| Issue | 問題 | 対策 |
|-------|------|------|
| **llama.cpp #7062** | LoRAマージ後のGGUF変換でファインチューニングデータが**ランダムに欠落** | HFで動作確認してから変換 |
| **Unsloth #611** | `save_pretrained_merged`が実際にはマージしない（adapter_model.binだけ保存） | `merge_and_unload(safe_merge=True)`使用 |
| **Unsloth #3091** | bfloat16でのマージ精度問題 | safe_merge=True使用 |
| **HuggingFace Discussion** | GGUF変換後のパフォーマンス低下 | F16で比較テスト |

### llama.cpp #7062 の重要な報告

> "GGUF conversion of the merged model does not produce the same output. The GGUF has lost some of its fine tune data, while still maintaining most of it."
> "I've tried F16, Q8, same issues. This is not a quantization issue."

**つまり**: GGUF変換自体がファインチューニングデータを損失する可能性がある！

### 安全なGGUF変換手順

```python
# Step 1: LoRAマージ（safe_merge=True推奨）
merged_model = model.merge_and_unload(safe_merge=True)

# Step 2: HuggingFace形式で保存
merged_model.save_pretrained("merged_model_16bit")
tokenizer.save_pretrained("merged_model_16bit")

# Step 3: HF形式で推論テスト（必須！）
# ここで問題があればGGUF変換に進まない

# Step 4: llama.cppでGGUF変換
# python convert_hf_to_gguf.py merged_model_16bit --outtype f16

# Step 5: F16 GGUFで推論テスト

# Step 6: 量子化
# llama-quantize model.f16.gguf model.Q4_K_M.gguf Q4_K_M
```

### bfloat16 マージ問題（Unsloth #3091）

PyTorch #115144で報告された問題:

- `nn.Linear` in bfloat16 ≠ `weight @ input + bias` in bfloat16
- 演算順序がbfloat16精度に影響
- LoRA重みはfloat32、ベースレイヤーはbfloat16 → 演算順序で結果が変わる
- `safe_merge=True` で緩和可能

```python
# 問題のあるコード（safe_merge=False）
delta_weight = self.get_delta_weight(active_adapter)
base_layer.weight.data += delta_weight

# 正しいコード（safe_merge=True）
delta_weight = self.get_delta_weight(active_adapter)
orig_weight += delta_weight.to(orig_dtype)
```

---

## ⚡ セクション4: 合成データ生成手法

### 最新手法比較（2024-2025）

**ソース**: TACL論文、arXiv、GitHub Awesome-LLM-Synthetic-Data

| 手法 | 説明 | 効果 | ソース |
|------|------|------|--------|
| **Self-Instruct** | LLMが自己生成 | ベースライン | Wang et al., 2023 |
| **Evol-Instruct** | 指示を進化させる | Self-Instructより上 | Xu et al., 2023 |
| **CRAFT** | コーパス検索+生成 | Evol-Instruct超え | TACL 2024 |
| **CoT-Self-Instruct** | CoT推論付き生成 | 推論タスクで優秀 | Meta FAIR, 2025 |

### CRAFT論文の重要な発見

> "CRAFT not only outperforms other fully synthetic data generation methods, such as Self-Instruct and Evol-Instruct, but also exhibits robustness to variations in the quality of the initial few shots."

つまり:

- CRAFTは初期few-shotの品質変動に強い
- タスク固有の合成データ生成に最適
- 人間がキュレーションしたデータセットと同等以上の性能

### noteAI向け合成データ戦略

```
[既存高品質データ 500件]
    ↓
[GPT-4等で品質スコアリング]
    ↓
[上位サンプルをシード]
    ↓
[CRAFTまたはEvol-Instruct適用]
    ↓
[合成データ生成 1000-2000件]
    ↓
[品質フィルタリング]
    ↓
[最終データセット]
```

---

## 🛡️ セクション5: 過学習検出の実装

### EarlyStoppingCallback使用方法

**ソース**: HuggingFace Discussions、philschmid.de

```python
from transformers import EarlyStoppingCallback

trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,  # 必須！
    args=TrainingArguments(
        evaluation_strategy="steps",
        eval_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
    ),
    callbacks=[
        EarlyStoppingCallback(early_stopping_patience=3)
    ],
)
```

### 過学習検出サイン（学術研究ベース）

**ソース**: Reddit、Kaggle、arXiv

```
🚨 確実な過学習サイン:
1. Train Loss↓ + Val Loss↑ = 過学習
2. Train Loss異常に低い（< 0.3）
3. 出力が訓練データのパターン繰り返し
4. 新規入力に対してゴミ or 無限ループ

📊 noteAI v1の症状（完全一致）:
- Loss: 2.847 → 0.254 (91%減少) ← 異常に低い
- Val Lossなし ← 検出不能
- 出力: 「」」」」」」」」」 ← 過学習の典型症状
```

Reddit r/MachineLearningより:
> "If train keeps going down but test goes up you're over[fitting]"

Kaggleガイドより:
> "Training loss goes down, but validation loss goes UP = Overfitting (model memorizing, not learning)"

---

## 📋 セクション6: 最終チェックリスト（究極版）

### 🔴 絶対に守るべき項目（これを破ると失敗）

1. **データ品質100%**: タグ形式・ゴミデータ0%
2. **Validation分割**: 最低80/20
3. **HF推論テスト**: GGUF変換前に必須
4. **EOS設定確認**: Qwenでは`<|im_end|>`が`eos_token`
5. **エポック1-3**: それ以上は過学習

### 🟡 強く推奨（破ると品質低下）

1. **train_on_responses_only**: 2-5%精度向上
2. **rsLoRA**: True推奨
3. **Cosine Scheduler**: 収束安定
4. **Early Stopping**: patience 3-5
5. **safe_merge=True**: マージ時

### 🟢 推奨（さらなる改善）

1. **合成データ増強**: CRAFTまたはEvol-Instruct
2. **LLM-as-Judge評価**: GPT-4でタイトル品質評価
3. **A/Bテスト**: 実運用での最終検証

---

## 🎯 セクション7: noteAI v2 実装計画

### Step 1: データクリーニング

```python
# data/processed/evol_instruct_data.jsonl から
# 1. タグフォーマット除去（28%）
# 2. 重複除去
# 3. 80/20 Train/Val分割
```

### Step 2: 訓練設定

```python
training_args = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    num_train_epochs=1,  # まず1エポック
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=5,
    evaluation_strategy="steps",
    eval_steps=20,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
)

callbacks = [EarlyStoppingCallback(early_stopping_patience=3)]
```

### Step 3: 検証プロセス

```
[訓練完了]
    ↓
[HF形式で5-10サンプルテスト] ← 最重要！
    ↓ 問題あり→データ/設定見直し
[F16 GGUF変換]
    ↓
[F16で推論テスト]
    ↓ 問題あり→変換プロセス確認
[Q4_K_M量子化]
    ↓
[最終テスト]
```

---

## 🔍 セクション8: v1失敗の最終診断

### 全ての証拠を踏まえた結論

| 観察された症状 | 可能な原因 | 確度 |
|----------------|-----------|------|
| 「」」」」」繰り返し | 過学習 / EOS問題 | 高 |
| F16でもQ4でも同じ症状 | 量子化は原因ではない | 確定 |
| Loss 91%減少 | 過学習の疑い | 高 |
| データ28%汚染 | モデルがゴミパターン学習 | 高 |
| Val分割なし | 過学習検出不能 | 確定 |

### 最も可能性の高い根本原因（複合要因）

1. **データ品質問題**: 28%のタグ形式データがモデルを汚染
2. **過学習**: Loss 0.254まで下がるのは異常 + Val監視なし
3. **EOS設定問題**: `<|im_end|>`が正しく学習されていない可能性
4. **GGUF変換問題**: llama.cpp #7062のようにデータ欠落した可能性

### v2で確実に成功するための優先順位

```
【最優先】
1. データクリーニング（タグ形式0%）
2. Train/Val分割（80/20）
3. HF推論テスト実施

【高優先】
4. エポック数削減（3→1）
5. EarlyStoppingCallback導入
6. EOS設定確認

【推奨】
7. safe_merge=True使用
8. F16段階でテスト
```

---

*作成日: 2025年1月*
*調査範囲: Qwen公式ドキュメント、GitHub Issues (llama.cpp, Unsloth, Axolotl)、学術論文 (TACL, arXiv)、Reddit (r/LocalLLaMA, r/MachineLearning)、Stack Exchange、Thinking Machines Lab*
