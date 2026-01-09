# 🚀 noteAI - 2026年世界最高水準タイトル生成AI

<p align="center">
  <strong>note.com特化型 AI タイトルジェネレーター</strong><br>
  「フォロワーが少なくてもスキが多い」記事のタイトルパターンを学習
</p>

---

## 🎯 プロジェクト概要

**目的**: インフルエンサーパワーに頼らず、純粋に「タイトルの力」だけで読者を惹きつける法則を統計的に学習したAIを作成する。

**コンセプト**: 「フォロワーが少ないのに、スキが多い記事」= 実力で売れるタイトル

---

## 🔥 2026年版 技術スタック

| 項目 | 技術 | 根拠（Web調査結果） |
|------|------|---------------------|
| **Framework** | Unsloth | 2-5x高速、80%省VRAM（2025年主流） |
| **Base Model** | ★★ Qwen3-14B | 16GB VRAMで動作（YouTube実証: 12GBで可能） |
| **代替1** | Qwen3-8B | 12GB VRAM用（日本語ベンチマーク最強） |
| **代替2** | Qwen3-4B | 8GB VRAM用（ファインチューニング後120B匹敵） |
| **量子化** | 4bit (bnb-4bit) | VRAM 75%削減、精度低下2-5%（Unslothで0%達成） |
| **Method** | QLoRA + rsLoRA | 高rank安定化、α/√r scaling |
| **Target** | All Layers | QLoRA-All が最高精度（attention+MLP） |
| **Training** | Completions Only | +1%精度向上（QLoRA論文） |
| **Format** | ChatML | Instruct向け最適 |

### 📚 参考文献・調査結果

- **Qwen3-14B**: "Fine-tune with just 12GB VRAM using Unsloth 4-bit quantization" (YouTube実証, 2025/5)
- **Unsloth**: "2-5x faster while using 80% less VRAM with zero accuracy degradation" (Medium, 2025)
- **4bit量子化**: "Saves 75% memory, 2.4x faster, 2-5% accuracy drop" (Newline.co)
- **rsLoRA**: "Almost doubled performance difference vs standard LoRA" (HuggingFace Blog)
- **All Layers**: "QLoRA-All performs best overall" (Unsloth Documentation)

---

## 📁 ファイル構成

```
noteAI/
├── README.md                          # このファイル
│
├── ## 🌟 2026年版（推奨）
├── train_unsloth_2026.ipynb           # ★ Unsloth + Qwen3-4B トレーニング
├── inference_2026.py                  # ★ 推論スクリプト
├── collect_power_data_v3.py           # Phase 1: データ収集（70キーワード）
├── prepare_training_data_v2.py        # Phase 2: Evol-Instruct形式
├── augment_data.py                    # Phase 2.5: 合成データ生成
│
├── ## 📂 データ
├── data/
│   ├── raw_notes_v3.jsonl             # 生データ
│   ├── processed/                     # 処理済み
│   │   ├── training_data.jsonl
│   │   └── evol_instruct_data.jsonl
│   └── augmented/                     # 拡張データ
│       └── augmented_training.jsonl
│
├── ## 📜 旧バージョン（参考）
├── train_model_colab_2026.ipynb       # HuggingFace PEFT版
├── train_model_colab.ipynb            # v1
├── collect_power_data.py              # v1
├── collect_power_data_v2.py           # v2
├── prepare_training_data.py           # v1
├── inference.py                       # v1
│
└── ## 🧪 テスト
    ├── test_api.py
    └── test_search_*.py
```

---

## 🚀 クイックスタート

### Step 1: データ収集

```bash
python collect_power_data_v3.py
```

**収集条件**:

- 70+キーワード（8カテゴリ）
- フォロワー10〜1000人（インフルエンサー除外）
- Power Score（スキ/フォロワー）計算

### Step 2: データ準備

```bash
python prepare_training_data_v2.py
python augment_data.py  # オプション：データ拡張
```

### Step 3: AI学習（Google Colab）

1. `train_unsloth_2026.ipynb` をGoogle Colabで開く
2. ランタイム → GPUに変更（T4以上推奨）
3. Google Driveをマウント
4. セルを順番に実行

**所要時間**:

- T4 GPU: ~30分（Unslothで高速化）
- A100 GPU: ~10分

### Step 4: 推論

```bash
# 単一生成
python inference_2026.py --model path/to/model --category "副業"

# 複数生成
python inference_2026.py --model path/to/model --category "AI活用" --n 5

# インタラクティブ
python inference_2026.py --model path/to/model --interactive
```

---

## 📊 技術仕様

### Power Score（実力スコア）

```
Power Score = スキ数 ÷ フォロワー数
```

| スコア | 意味 |
|--------|------|
| > 1.0 | フォロワー数以上のスキ → **超優秀** |
| 0.5〜1.0 | フォロワーの半数以上 → 優秀 |
| 0.1〜0.5 | 標準的 |
| < 0.1 | 低パフォーマンス |

### LoRA設定（2026年ベストプラクティス）

```python
LoraConfig(
    r=32,                    # rank: 16-32で十分
    lora_alpha=64,           # 2*r
    use_rslora=True,         # ★ rsLoRA: α/√r scaling
    target_modules=[         # ★ 全層ターゲット
        "q_proj", "k_proj", "v_proj", "o_proj",  # Attention
        "gate_proj", "up_proj", "down_proj",     # MLP
    ],
)
```

### モデル選択ガイド（2025-2026 Web調査結果）

| GPU VRAM | 推奨モデル | HuggingFace ID | 学習時VRAM |
|----------|-----------|----------------|-----------|
| ~8GB | Qwen3-4B | `unsloth/Qwen3-4B-bnb-4bit` | ~6-8GB |
| ~12GB | Qwen3-14B | `unsloth/Qwen3-14B-bnb-4bit` | ~12GB |
| ★★ **16GB** | **Qwen3-14B** | `unsloth/Qwen3-14B-bnb-4bit` | ~12-14GB |
| ~17.5GB+ | Qwen3-30B-A3B | `unsloth/Qwen3-30B-A3B-bnb-4bit` | ~17.5GB |

> **💡 重要発見**: YouTube実証（2025/5）により **Qwen3-14Bが12GB VRAMでファインチューニング可能**と確認！
> あなたの16GB VRAMなら**Qwen3-14B**が余裕で動作します。

---

## 📈 調査結果サマリー

### ベースモデル比較（ファインチューニング後性能）

| モデル | 日本語性能 | Fine-tuning後 | 推奨度 |
|--------|-----------|---------------|--------|
| **Qwen3-4B** | ★★★★☆ | ★★★★★ | ◎ 最推奨（120B匹敵） |
| Qwen2.5-7B | ★★★★★ | ★★★★☆ | ○ バランス良 |
| Llama-3.3-8B | ★★★★☆ | ★★★★☆ | △ 英語向け |
| rinna/neox-3.6b | ★★★☆☆ | ★★★☆☆ | × 旧世代 |

### PEFT手法比較

| 手法 | 精度向上 | 速度 | 推奨 |
|------|----------|------|------|
| **rsLoRA** | +1-2% | 1.0x | ★ 推奨 |
| DoRA | +3-4% | 0.12x (8x遅い) | △ 時間あれば |
| LoRA+ | +1-2% | 2.0x | ○ 良い |
| Standard LoRA | baseline | 1.0x | - |

---

## 🔧 環境構築

### ローカル環境

```bash
pip install torch transformers peft accelerate bitsandbytes
pip install datasets trl sentencepiece
```

### Unsloth（推奨）

```bash
pip install unsloth
```

### 推奨スペック

| 項目 | 最小 | 推奨 |
|------|------|------|
| Python | 3.10 | 3.11 |
| GPU VRAM | 8GB | 16GB+ |
| RAM | 16GB | 32GB |
| CUDA | 11.8 | 12.1 |

---

## 📝 API仕様（note.com）

### 確認済みエンドポイント

| API | URL | 取得データ |
|-----|-----|-----------|
| 検索 | `GET /api/v3/searches?q={keyword}&size=20` | 記事・ユーザー |
| ユーザー | `GET /api/v2/creators/{urlname}` | フォロワー数等 |
| 記事一覧 | `GET /api/v2/creators/{urlname}/contents` | タイトル・スキ数 |

### ⚠️ 注意事項

- アクセス間隔: 1.5秒以上
- ヘッダー: User-Agent必須
- 用途: 学習・研究目的のみ

---

## 🛣️ ロードマップ

- [x] Phase 1: データ収集（70キーワード）
- [x] Phase 2: Evol-Instruct形式データ準備
- [x] Phase 2.5: 合成データ拡張
- [x] Phase 3: Unsloth + Qwen2.5 学習環境
- [ ] Phase 4: モデル学習・評価
- [ ] Phase 5: Ollama/vLLMデプロイ

---

## ⚖️ 免責事項

このプロジェクトは学習・研究目的です。

- note.comの利用規約を遵守してください
- サーバーに負荷をかけないよう配慮してください
- 収集データの商用利用・公開は避けてください

---

## 📚 参考リンク

- [Unsloth GitHub](https://github.com/unslothai/unsloth)
- [Qwen2.5 HuggingFace](https://huggingface.co/Qwen)
- [PEFT Documentation](https://huggingface.co/docs/peft)
- [rsLoRA Paper](https://arxiv.org/abs/2312.03732)

---

<p align="center">
  <strong>Built with 🔥 Unsloth + 🤗 HuggingFace</strong><br>
  2026年1月 - 世界最高水準
</p>
