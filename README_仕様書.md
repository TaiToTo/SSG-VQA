# SSG-VQA リバースエンジニアリング完全ドキュメント

このリポジトリのリバースエンジニアリング結果をまとめたドキュメント集です。

## 📚 ドキュメント一覧

### 1. [SSG-VQA_仕様書.md](./SSG-VQA_仕様書.md) 【メインドキュメント】
**推奨読者**: 全員

システム全体の詳細な仕様書です。以下の内容を網羅しています:

- **システムアーキテクチャ全体像**
- **データ構造の完全な説明**
  - シーングラフのJSON形式
  - QAペアのフォーマット
  - 視覚特徴の構成
- **モデルアーキテクチャ**: SSG-VQA-Net
- **訓練・テストパイプライン**
- **主要ファイル構成**
- **シーングラフからVQAへの流れ**
- **ハイパーパラメータ一覧**
- **シーングラフの関係性表現の仕組み**
- **質問応答の推論フロー**
- **性能評価とベンチマーク**

### 2. [SSG-VQA_実装詳細と例.md](./SSG-VQA_実装詳細と例.md) 【実装参考用】
**推奨読者**: 開発者、実装を理解したい方

具体的なコード例とデータ例を多数含む実装ガイドです:

- **シーングラフの具体例** (実際のJSONデータ付き)
- **質問生成の実例** (実際のQAテキスト付き)
- **視覚特徴抽出の詳細実装**
  - ROI特徴抽出のコード解説
  - 530次元ベクトルの詳細構成
- **モデル推論の流れ** (ステップバイステップ)
- **コードウォークスルー**
  - 訓練ループの詳細
  - データローダーの動作
  - 評価関数の実装
- **よくある処理のパターン**
  - シーングラフのクエリ方法
  - 空間関係の検索
  - 複合条件の処理
- **デバッグのヒント**

### 3. [SSG-VQA_システム概要図.md](./SSG-VQA_システム概要図.md) 【ビジュアルガイド】
**推奨読者**: 全体像を素早く把握したい方

図とビジュアルを中心としたシステム概要:

- **データ生成パイプライン** (Mermaid図)
- **訓練パイプライン** (Mermaid図)
- **推論・評価フロー** (Mermaid図)
- **クラス・データ構造関係図**
- **シーングラフの関係性マトリクス**
- **視覚特徴の構成図**
- **質問の複雑度レベル別解説**
- **モデルアーキテクチャの詳細図**
- **評価メトリクスの説明**
- **データセット統計の可視化**
- **ファイルサイズと要件**

---

## 🎯 推奨読読順序

### 初めての方
1. [SSG-VQA_システム概要図.md](./SSG-VQA_システム概要図.md) で全体像を把握
2. [SSG-VQA_仕様書.md](./SSG-VQA_仕様書.md) で詳細を理解
3. [SSG-VQA_実装詳細と例.md](./SSG-VQA_実装詳細と例.md) で具体的な実装を確認

### 開発者の方
1. [SSG-VQA_仕様書.md](./SSG-VQA_仕様書.md) でシステム全体を把握
2. [SSG-VQA_実装詳細と例.md](./SSG-VQA_実装詳細と例.md) でコード詳細を理解
3. [SSG-VQA_システム概要図.md](./SSG-VQA_システム概要図.md) で必要な図を参照

### 研究者の方
1. [SSG-VQA_仕様書.md](./SSG-VQA_仕様書.md) でモデルアーキテクチャと評価を確認
2. [SSG-VQA_システム概要図.md](./SSG-VQA_システム概要図.md) でデータ構造を把握
3. [SSG-VQA_実装詳細と例.md](./SSG-VQA_実装詳細と例.md) で実装詳細を参照

---

## 🔍 システム概要（クイックサマリー）

### SSG-VQA とは？

**Surgical Scene Graph - Visual Question Answering** は、手術映像における器具と臓器の関係をグラフ構造で表現し、それを基に視覚的質問応答を行うシステムです。

### 主要コンポーネント

```
1. シーングラフ (Scene Graph)
   └─ 器具・臓器のオブジェクトと空間的・動作的関係性

2. 質問応答ペア (QA Pairs)
   └─ シーングラフから自動生成された960k個のQAペア

3. 視覚特徴 (Visual Features)
   └─ ResNet18 + ROI Align による530次元ベクトル

4. SSG-VQA-Net モデル
   └─ VisualBERT ベースのマルチモーダル融合モデル
```

### データフロー

```
手術ビデオ
  ↓
物体検出・セグメンテーション
  ↓
シーングラフ生成 (JSON)
  ↓
├─→ 質問生成エンジン → QAペア (txt)
└─→ 視覚特徴抽出 → ROI特徴 (HDF5)
     ↓
  モデル訓練 (train.py)
     ↓
  SSG-VQA-Net
     ↓
  推論・評価 (test.py)
```

### 主要な革新点

1. **シーングラフ知識の統合**: 空間的・動作的関係を明示的にモデル化
2. **Scene-embedded Interaction Module (SIM)**: テキストと視覚のクロスモーダルアテンション
3. **多様な質問生成**: 複雑度レベル（zero-hop, one-hop, single-and, compare）
4. **ROIベース特徴**: オブジェクトごとの詳細な視覚特徴

---

## 📊 データセット統計

| 項目 | 数値 |
|------|------|
| 総QAペア数 | 960,000 |
| ユニーク質問数 | 501,000 |
| フレーム数 | ~25,000 |
| ビデオ数 | 45 |
| シーングラフJSON数 | 100,863+ |
| 平均QA数/フレーム | 38.9 |

---

## 🏗️ ファイル構造

```
SSG-VQA/
├── train.py                              # 訓練スクリプト
├── test.py                               # テストスクリプト
├── models/
│   ├── VisualBertClassification_ssgqa.py # メインモデル
│   ├── VisualBert_ssgqa.py              # VisualBERTエンコーダ
│   └── resnets.py                        # ResNet特徴抽出
├── utils/
│   ├── dataloaderClassification.py       # データローダー
│   ├── feat_extract_visual.py            # 画像特徴抽出
│   ├── feature_extract_roi.py            # ROI特徴抽出
│   └── utils.py                          # ユーティリティ
├── data/
│   ├── qa_txt/                           # QAテキストファイル
│   │   └── VID*/
│   │       └── *.txt                     # 質問|答え|メタデータ
│   └── visual_feats/
│       ├── cropped_images/               # 画像全体特徴 (HDF5)
│       └── roi_yolo_coord/               # ROI特徴 (HDF5)
├── scene_graph/                          # シーングラフJSON
│   └── VID*_*.json                       # オブジェクト+関係性
├── checkpoints/                          # モデルチェックポイント
│   └── experiment*/
│       └── Best.pth.tar
│
└── ドキュメント (このフォルダ)
    ├── SSG-VQA_仕様書.md
    ├── SSG-VQA_実装詳細と例.md
    ├── SSG-VQA_システム概要図.md
    └── README_仕様書.md (このファイル)
```

---

## 🚀 クイックスタート

### 環境セットアップ
```bash
conda env create -f environment.yml
conda activate ssgvqa
```

### データダウンロード
```bash
# QAペア
wget https://s3.unistra.fr/camma_public/github/ssg-qa/ssg-qa.zip
unzip ssg-qa.zip -d ./data/qa_txt

# 視覚特徴
wget https://s3.unistra.fr/camma_public/github/ssg-qa/cropped_images.zip
wget https://s3.unistra.fr/camma_public/github/ssg-qa/roi_yolo_coord.zip
unzip cropped_images.zip -d ./data/visual_feats
unzip roi_yolo_coord.zip -d ./data/visual_feats
```

### 訓練
```bash
python train.py \
    --batch_size 64 \
    --epochs 80 \
    --lr 0.0001 \
    --encoder_layer 6 \
    --n_heads 8 \
    --folder_head ./data/ \
    --folder_tail '/*.txt'
```

### テスト
```bash
python test.py \
    --checkpoint ./checkpoints/experiment1/Best.pth.tar \
    --folder_head ./data/ \
    --folder_tail '/*.txt'
```

---

## 🎓 主要概念の説明

### シーングラフとは？

シーングラフは、手術シーン内のオブジェクト（器具・臓器）とその関係性を構造化したデータです。

**オブジェクト**:
- 位置 (bbox, center)
- 名前 (component)
- タイプ (anatomy / instrument)

**関係性**:
- 空間: above, below, left, right, within
- 動作: grasp, horizontal

### 質問の複雑度レベル

1. **Zero-hop**: 直接的な属性
   - 例: "How many graspers are there?"

2. **One-hop**: 1段階の関係推論
   - 例: "What is to the left of the gallbladder?"

3. **Single-and**: 複数条件の同時満足
   - 例: "What is right of X and above Y?"

4. **Compare**: 比較・計算
   - 例: "Are there more instruments than anatomies?"

### 視覚特徴 (530次元)

```
[0:14]   クラスベクトル (one-hot, 14クラス)
[14:18]  正規化bbox座標 (x1, y1, x2, y2)
[18:530] ResNet18視覚特徴 (512次元)
```

### モデルアーキテクチャ

```
質問テキスト → BERTトークナイザー → テキスト埋め込み
                                          ↓
視覚特徴 (530×20) → ビジュアル埋め込み → VisualBERT (6層)
                                          ↓
                                    Pooler (1024)
                                          ↓
                                   分類層 (1024→52)
                                          ↓
                                      答えクラス
```

---

## 📈 性能

| メトリック | 値 |
|----------|-----|
| Accuracy | ~72-75% |
| mAP | ~68-71% |
| mAR | ~67-70% |
| mAF1 | ~68-70% |
| wF1 | ~71-74% |

**質問タイプ別**:
- Zero-hop: ~80%
- One-hop: ~70%
- Single-and: ~65%
- Compare: ~60%

---

## 💡 使用例

### シーングラフからの情報抽出

```python
import json

with open('scene_graph/VID01_0.json', 'r') as f:
    sg = json.load(f)

# 器具を探す
instruments = [obj for obj in sg['scenes'][0]['objects'] 
               if obj['type'] == 'instrument']

# 把持関係を探す
grasp_relations = sg['scenes'][0]['relationships']['grasp']
```

### モデルでの推論

```python
from transformers import BertTokenizer
import torch

# 質問をトークナイズ
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
inputs = tokenizer("What is being grasped?", 
                   return_tensors="pt", 
                   max_length=77)

# 視覚特徴をロード
visual_features = load_visual_features("VID01", 262)

# 推論
model.eval()
with torch.no_grad():
    outputs = model(inputs, visual_features)
    predicted = torch.argmax(outputs, dim=1)
    answer = labels[predicted]
```

---

## 🔗 参考リンク

- **論文**: [Advancing Surgical VQA with Scene Graph Knowledge](https://arxiv.org/abs/2312.10251)
- **公式リポジトリ**: [CAMMA-public/SSG-VQA](https://github.com/CAMMA-public/SSG-VQA)
- **データセット**: [CAMMA Datasets](http://camma.u-strasbg.fr/datasets)

---

## 📝 補足資料

### 既存のドキュメント

このリポジトリには元々以下のドキュメントがあります:
- `README.md`: 公式README
- `SETUP_NOTES.md`: セットアップ手順
- `SETUP_SUMMARY.md`: セットアップサマリー
- `CHOLECT50_COMPATIBILITY.md`: CholecT50互換性

### 新規作成したドキュメント

本リバースエンジニアリングで作成したドキュメント:
- `SSG-VQA_仕様書.md`: **完全な技術仕様書**
- `SSG-VQA_実装詳細と例.md`: **実装ガイド**
- `SSG-VQA_システム概要図.md`: **ビジュアルガイド**
- `README_仕様書.md`: **このファイル（索引）**

---

## 🙋 よくある質問

### Q1: シーングラフはどこから来るのか？
A: 手術画像に対して物体検出・セグメンテーションモデルを実行し、検出されたオブジェクトの位置関係と動作関係を計算して生成されます。

### Q2: 質問はどうやって生成されるのか？
A: シーングラフの構造を基に、テンプレートベースの質問生成エンジンが自動的に生成します。

### Q3: モデルはどのように訓練されるのか？
A: 質問（テキスト）と視覚特徴（画像）をVisualBERTに入力し、52クラスの答えを予測するマルチクラス分類タスクとして訓練されます。

### Q4: ROI特徴とは何か？
A: Region of Interest（関心領域）特徴のことで、シーングラフの各オブジェクト領域に対してROI Alignを用いて抽出された530次元の特徴ベクトルです。

### Q5: なぜVisualBERTを使うのか？
A: テキストと視覚情報を効果的に融合できるマルチモーダルTransformerモデルだからです。特にSIMモジュールでシーングラフの幾何学的知識を統合できます。

---

## 📧 お問い合わせ

このドキュメントに関する質問や改善提案があれば、リポジトリのIssueまでお願いします。

---

**作成日**: 2026年3月30日  
**バージョン**: 1.0  
**作成者**: リバースエンジニアリングプロジェクト
