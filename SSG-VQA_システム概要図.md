# SSG-VQA システム概要図

## 全体構成の3段階

### 段階1: データ準備（前処理）

```mermaid
graph LR
    subgraph "入力データ"
        Video[手術ビデオ]
        Frame[フレーム画像<br/>480×860]
    end
    
    subgraph "物体検出"
        YOLO[YOLO検出器]
        Seg[セグメンテーション]
    end
    
    subgraph "シーングラフ構築"
        ObjList[オブジェクトリスト]
        BBox[BBox座標]
        SpatialRel[空間関係計算]
        ActionRel[動作関係抽出]
    end
    
    subgraph "データ生成"
        SGJSON[scene_graph/<br/>VID*_*.json]
        QAGen[質問生成エンジン]
        QATXT[data/qa_txt/<br/>*.txt]
    end
    
    subgraph "特徴抽出"
        ResNet[ResNet18]
        ROIPool[ROI Align]
        VisFeats[視覚特徴<br/>530次元×20]
    end
    
    Video --> Frame
    Frame --> YOLO
    Frame --> Seg
    
    YOLO --> ObjList
    Seg --> ObjList
    ObjList --> BBox
    
    BBox --> SpatialRel
    ObjList --> ActionRel
    
    ObjList --> SGJSON
    BBox --> SGJSON
    SpatialRel --> SGJSON
    ActionRel --> SGJSON
    
    SGJSON --> QAGen
    QAGen --> QATXT
    
    Frame --> ResNet
    SGJSON --> ROIPool
    ResNet --> ROIPool
    ROIPool --> VisFeats
    
    style SGJSON fill:#e1f5ff
    style QATXT fill:#ffe1f5
    style VisFeats fill:#e1ffe1
```

### 段階2: モデル訓練

```mermaid
graph TB
    subgraph "データセット"
        QA[QA Pairs<br/>960k pairs]
        VF[Visual Features<br/>HDF5 files]
    end
    
    subgraph "データローダー"
        Load[ファイル読み込み]
        Batch[バッチ作成<br/>batch_size=64]
    end
    
    subgraph "モデル入力"
        Q[質問テキスト]
        V[視覚特徴<br/>20×530]
        L[ラベル<br/>答えクラス]
    end
    
    subgraph "VisualBert"
        Tok[Tokenizer<br/>BERT]
        TEmb[Text Embedding<br/>77×1024]
        VEmb[Visual Projection<br/>20×1024]
        
        subgraph "Transformer×6"
            SA[Self-Attention]
            CA[Cross-Attention]
            FF[Feed Forward]
        end
        
        Pool[Pooler<br/>1024]
    end
    
    subgraph "出力処理"
        Cls[Classifier<br/>1024→52]
        Loss[Cross Entropy Loss]
        Opt[Adam Optimizer]
    end
    
    QA --> Load
    VF --> Load
    Load --> Batch
    
    Batch --> Q
    Batch --> V
    Batch --> L
    
    Q --> Tok --> TEmb
    V --> VEmb
    
    TEmb --> SA
    VEmb --> SA
    SA --> CA --> FF --> Pool
    
    Pool --> Cls
    L --> Loss
    Cls --> Loss
    Loss --> Opt
    Opt -.更新.-> VisualBert
    
    style Loss fill:#ffcccc
    style Opt fill:#ccffcc
```

### 段階3: 推論・評価

```mermaid
flowchart LR
    subgraph "入力"
        NewQ[新しい質問]
        NewImg[手術画像]
    end
    
    subgraph "前処理"
        ExtractVis[視覚特徴抽出]
        TokenizeQ[質問トークナイズ]
    end
    
    subgraph "推論"
        Model[学習済みモデル<br/>SSG-VQA-Net]
        Softmax[Softmax]
    end
    
    subgraph "出力"
        Pred[予測答え]
        Conf[信頼度]
    end
    
    NewQ --> TokenizeQ
    NewImg --> ExtractVis
    
    TokenizeQ --> Model
    ExtractVis --> Model
    
    Model --> Softmax
    Softmax --> Pred
    Softmax --> Conf
    
    style Model fill:#ffebcd
    style Pred fill:#98fb98
```

---

## クラス・データ構造

```mermaid
classDiagram
    class SceneGraph {
        +List~Object~ objects
        +Dict relationships
        +String image_filename
        +Dict info
    }
    
    class Object {
        +List~int~ bbox
        +String component
        +String type
        +List~float~ center
        +String location
    }
    
    class Relationships {
        +List~List~ above
        +List~List~ below
        +List~List~ left
        +List~List~ right
        +List~List~ within
        +List~List~ grasp
        +List~List~ horizontal
    }
    
    class VisualFeature {
        +Array class_vector [14]
        +Array bbox_norm [4]
        +Array resnet_features [512]
        +getTensor() Tensor
    }
    
    class QAPair {
        +String question
        +String answer
        +String template_type
        +String question_category
        +parse() Tuple
    }
    
    class VisualBertModel {
        +VisualBertEncoder encoder
        +Linear classifier
        +forward(inputs, visual) outputs
    }
    
    SceneGraph "1" *-- "N" Object
    SceneGraph "1" *-- "1" Relationships
    Object "1" --> "1" VisualFeature : generates
    SceneGraph "1" --> "N" QAPair : generates
    QAPair "1" --> "1" VisualFeature : requires
    VisualBertModel ..> VisualFeature : uses
    VisualBertModel ..> QAPair : processes
```

---

## シーングラフの関係性マトリクス

シーングラフの関係性は、N×N マトリクスではなく、**オブジェクトごとのリスト**として表現されます。

### 例: 6オブジェクトのシーン

| Index | Component | Type |
|-------|-----------|------|
| 0 | abdominal_wall | anatomy |
| 1 | liver | anatomy |
| 2 | gut | anatomy |
| 3 | omentum | anatomy |
| 4 | gallbladder | anatomy |
| 5 | grasper | instrument |

### Above 関係（上方向）

```
relationships['above'] = [
    [5],              # 0番は5番の上
    [5],              # 1番は5番の上
    [0,1,4,5],        # 2番は0,1,4,5番の上
    [0,1,4,5],        # 3番は0,1,4,5番の上
    [5],              # 4番は5番の上
    []                # 5番は何の上にもない
]
```

**解釈**: `relationships['above'][i]` は「iが上にあるオブジェクトのインデックスリスト」

### Grasp 関係（把持）

```
relationships['grasp'] = [
    [],  # 0番は何も把持していない
    [],  # 1番は何も把持していない
    [],  # 2番は何も把持していない
    [],  # 3番は何も把持していない
    [],  # 4番は何も把持していない
    [4]  # 5番(grasper)は4番(gallbladder)を把持
]
```

### 関係性の可視化

```mermaid
graph TD
    subgraph "空間配置（Y軸: 上→下）"
        A[abdominal_wall<br/>index:0]
        B[liver<br/>index:1]
        C[gallbladder<br/>index:4]
        D[grasper<br/>index:5]
        E[gut<br/>index:2]
        F[omentum<br/>index:3]
    end
    
    D -->|above| A
    D -->|above| B
    D -->|above| E
    D -->|above| F
    D -->|above| C
    
    D -.->|grasp| C
    
    B -->|within| C
    
    style D fill:#ffcccc
    style C fill:#ccffff
```

---

## 視覚特徴の構成

### ROI特徴ベクトル (530次元)

```
╔═══════════════════════════════════════════════════════════╗
║  Visual Feature Vector (530 dimensions)                  ║
╠═══════════════════════════════════════════════════════════╣
║  [0:14]   Class One-Hot Vector                           ║
║           ┌─────────────────────────────┐                ║
║           │ 14 object classes           │                ║
║           │ (anatomy + instrument)      │                ║
║           └─────────────────────────────┘                ║
╠═══════════════════════════════════════════════════════════╣
║  [14:18]  Normalized BBox Coordinates                    ║
║           ┌─────────────────────────────┐                ║
║           │ x1/860, y1/480,             │                ║
║           │ x2/860, y2/480              │                ║
║           └─────────────────────────────┘                ║
╠═══════════════════════════════════════════════════════════╣
║  [18:530] ResNet18 Visual Features                       ║
║           ┌─────────────────────────────┐                ║
║           │ 512-dim feature vector      │                ║
║           │ from ROI Align              │                ║
║           └─────────────────────────────┘                ║
╚═══════════════════════════════════════════════════════════╝
```

### 特徴抽出プロセス

```mermaid
flowchart TB
    Img[手術画像<br/>480×860×3]
    
    subgraph "ResNet18特徴抽出"
        Conv[畳み込み層×多数]
        FMap[特徴マップ<br/>H'×W'×512]
    end
    
    subgraph "各オブジェクトに対して"
        BBox[BBox座標]
        ROI[ROI Align<br/>spatial_scale=0.031]
        Pool[1×1 Pooling]
        Feat512[512次元特徴]
    end
    
    subgraph "特徴結合"
        Class[クラス14次元]
        Norm[正規化bbox 4次元]
        Concat[連結]
        Final[530次元ベクトル]
    end
    
    Img --> Conv --> FMap
    FMap --> ROI
    BBox --> ROI
    ROI --> Pool --> Feat512
    
    Class --> Concat
    Norm --> Concat
    Feat512 --> Concat
    Concat --> Final
    
    style Final fill:#98fb98
```

---

## 質問の複雑度レベル

### Zero-hop: 直接属性

```mermaid
graph LR
    Q[質問: How many<br/>graspers are there?]
    
    subgraph "推論"
        S[シーン全体]
        C[カウント]
    end
    
    Q --> S --> C
    C --> A[答え: 1]
    
    style Q fill:#e1f5ff
    style A fill:#e1ffe1
```

**例**:
- "How many instruments are present?"
- "What color is the liver?"
- "Is there a grasper?"

### One-hop: 1段階の関係推論

```mermaid
graph LR
    Q[質問: What is to the<br/>left of gallbladder?]
    
    subgraph "推論"
        O1[gallbladder特定]
        R1[left関係を参照]
        O2[対象オブジェクト]
    end
    
    Q --> O1 --> R1 --> O2
    O2 --> A[答え: cystic_plate]
    
    style Q fill:#e1f5ff
    style A fill:#e1ffe1
    style R1 fill:#ffffcc
```

**例**:
- "What is above the liver?"
- "What color is the object to the right of X?"
- "How many instruments are grasping the gallbladder?"

### Single-and: 複数条件の同時満足

```mermaid
graph TB
    Q[質問: What is to the right of X<br/>AND above Y?]
    
    subgraph "推論"
        O1[X を特定]
        O2[Y を特定]
        R1[right関係]
        R2[above関係]
        Inter[積集合]
    end
    
    Q --> O1
    Q --> O2
    O1 --> R1
    O2 --> R2
    R1 --> Inter
    R2 --> Inter
    Inter --> A[答え: Z]
    
    style Q fill:#e1f5ff
    style A fill:#e1ffe1
    style Inter fill:#ffcccc
```

**例**:
- "How many objects are right of X and above Y?"
- "What is within X and below Y?"

### Compare: 比較・計算

```mermaid
graph LR
    Q[質問: Are there more<br/>instruments than anatomies?]
    
    subgraph "推論"
        C1[器具をカウント]
        C2[臓器をカウント]
        Comp[比較]
    end
    
    Q --> C1
    Q --> C2
    C1 --> Comp
    C2 --> Comp
    Comp --> A[答え: False]
    
    style Q fill:#e1f5ff
    style A fill:#e1ffe1
    style Comp fill:#ffccff
```

**例**:
- "Is the number of graspers greater than 2?"
- "Are there equal numbers of instruments and anatomies?"

---

## モデルアーキテクチャの詳細

### VisualBERT の構造

```
入力層
├─ テキストトークン: 77 tokens
└─ 視覚トークン: 20 objects

埋め込み層
├─ Token Embedding (語彙: 30522)
├─ Position Embedding (最大: 512)
├─ Token Type Embedding (2種類: text/visual)
└─ 埋め込みサイズ: 1024

Transformer エンコーダ × 6層
├─ Multi-Head Self-Attention (8 heads)
│  ├─ Query/Key/Value 変換
│  ├─ Attention 計算
│  └─ Concat & Linear
├─ Add & Norm
├─ Feed Forward Network
│  ├─ Linear (1024 → 4096)
│  ├─ GELU Activation
│  └─ Linear (4096 → 1024)
└─ Add & Norm

出力層
├─ Pooler (CLS token)
├─分類線形層 (1024 → 52)
└─ Softmax
```

### アテンションの流れ

```mermaid
graph TB
    subgraph "入力トークン (97 tokens)"
        CLS[CLS]
        T1[text_1]
        T2[text_2]
        TN[text_77]
        V1[visual_1]
        V2[visual_2]
        VN[visual_20]
    end
    
    subgraph "Self-Attention"
        SA[全トークン間で<br/>相互アテンション]
    end
    
    subgraph "Scene-Embedded Interaction"
        CA[Text ↔ Visual<br/>Cross-Attention]
    end
    
    CLS --> SA
    T1 --> SA
    T2 --> SA
    TN --> SA
    V1 --> SA
    V2 --> SA
    VN --> SA
    
    SA --> CA
    CA --> Out[出力特徴]
    
    style CA fill:#ffebcd
    style Out fill:#98fb98
```

---

## 評価メトリクス

### マルチクラス分類の評価

```
Accuracy = 正しく予測したサンプル数 / 全サンプル数

Precision (適合率) = TP / (TP + FP)
各クラスで計算し、マクロ平均

Recall (再現率) = TP / (TP + FN)
各クラスで計算し、マクロ平均

F1-score = 2 × (Precision × Recall) / (Precision + Recall)
```

### 典型的な性能（論文より）

| メトリック | SSG-VQA-Net |
|----------|-------------|
| Accuracy | ~72-75% |
| mAP | ~68-71% |
| mAR | ~67-70% |
| mAF1 | ~68-70% |
| wF1 | ~71-74% |

**質問タイプ別**:
- Zero-hop: 高精度 (~80%)
- One-hop: 中精度 (~70%)
- Single-and: 向上が顕著 (~65%)
- Compare: やや低め (~60%)

---

## データセット統計の可視化

### QAペアの分布

```
質問タイプ別分布:
┌────────────────────────────────────────┐
│ Count      ████████████████  40%       │
│ Exist      ████████████      30%       │
│ Query      ████████          20%       │
│ Compare    ████              10%       │
└────────────────────────────────────────┘

複雑度別分布:
┌────────────────────────────────────────┐
│ Zero-hop   ██████████        25%       │
│ One-hop    ████████████████  40%       │
│ Single-and ████████████      30%       │
│ Compare    ██                5%        │
└────────────────────────────────────────┘

答えクラス別分布:
┌────────────────────────────────────────┐
│ Numbers    ████████          20%       │
│ Bool       ████████          20%       │
│ Anatomy    ████████████      30%       │
│ Instrument ████████          20%       │
│ Other      ████              10%       │
└────────────────────────────────────────┘
```

### ビデオ・フレーム統計

```
ビデオ数: 45 (VID01-VID80 から選択)
総フレーム数: ~25,000
総QAペア数: 960,000
ユニーク質問数: 501,000

平均値:
- QAペア/フレーム: 38.9
- オブジェクト/フレーム: 5-8
- 器具/フレーム: 1-3
- 臓器/フレーム: 3-6
```

---

## ファイルサイズと要件

### ストレージ要件

```
scene_graph/          : ~500 MB  (100,863 JSONファイル)
data/qa_txt/          : ~1.2 GB  (テキストファイル)
data/visual_feats/    : ~15 GB   (HDF5特徴ファイル)
  ├─ cropped_images/  : ~8 GB
  └─ roi_yolo_coord/  : ~7 GB
checkpoints/          : ~500 MB  (モデルチェックポイント)

合計: ~17 GB
```

### 計算要件

**訓練**:
- GPU: 8-16 GB VRAM (推奨: NVIDIA RTX 3090以上)
- RAM: 32 GB以上
- 訓練時間: ~20-30時間 (80エポック、1 GPU)

**推論**:
- GPU: 4-8 GB VRAM
- RAM: 16 GB
- 推論速度: ~50 QA/秒 (バッチサイズ32)

---

## まとめ: システムの特徴

### 革新的な点

1. **シーングラフ知識の統合**
   - 空間関係と動作関係を明示的にモデル化
   - 幾何学的推論能力の向上

2. **Scene-embedded Interaction Module (SIM)**
   - テキストと視覚のクロスモーダルアテンション
   - シーングラフの構造情報を活用

3. **多様な質問生成**
   - テンプレートベースで複雑度制御
   - 960kの大規模QAデータセット

4. **ROIベースの視覚特徴**
   - オブジェクトごとの詳細特徴
   - クラス + 位置 + 視覚情報の統合

### 応用可能性

- **手術支援システム**: リアルタイムVQA
- **手術教育**: 対話的な学習ツール
- **手術記録分析**: 自動レポート生成
- **ロボット手術**: 状況認識と意思決定

このシステムは、手術シーンの理解において、従来の画像のみのVQAを大きく超える性能を実現しています。
