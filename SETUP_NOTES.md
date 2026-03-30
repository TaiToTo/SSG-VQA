# SSG-VQA セットアップ備忘録

## 環境情報
- **セットアップ日**: 2026年3月30日
- **Python バージョン**: 3.13.3
- **パッケージマネージャ**: uv
- **OS**: macOS

## セットアップ手順

### 1. 仮想環境の作成
```bash
uv venv --python 3.13
source .venv/bin/activate
```

### 2. 主要パッケージのインストール
元の`requirements.txt`は古いバージョン指定で互換性問題があったため、最新バージョンでインストール：

```bash
# PyTorchを先にインストール
uv pip install torch torchvision

# 主要なパッケージをインストール
uv pip install transformers datasets scikit-learn scipy pandas numpy \
  matplotlib opencv-python tqdm einops timm tensorboard wandb

# CLIP、spacy等をインストール
uv pip install git+https://github.com/openai/CLIP.git spacy torchmetrics
```

### 3. インストールされた主要パッケージ（最新版）
- **torch**: 2.11.0
- **torchvision**: 0.26.0
- **transformers**: 5.4.0
- **datasets**: 4.8.4
- **numpy**: 2.4.4
- **pandas**: 3.0.1
- **scikit-learn**: 1.8.0
- **scipy**: 1.17.1
- **matplotlib**: 3.10.8
- **opencv-python**: 4.13.0.92
- **spacy**: 3.8.14
- **CLIP**: 1.0 (from GitHub)
- **timm**: 1.0.26
- **tensorboard**: 2.20.0
- **wandb**: 0.25.1
- **torchmetrics**: 1.9.0

## 元のセットアップとの違い

### オリジナル（README.mdに記載）
- Python 3.8
- PyTorch 1.7.1
- CUDA 10.2
- Anaconda3使用

### 現在の環境
- Python 3.13.3
- PyTorch 2.11.0
- uvによる依存関係管理
- 最新版パッケージ使用

## 注意事項

### 1. 古いrequirements.txtについて
- 元の`requirements.txt`は2022年頃のパッケージバージョンで固定されている
- Python 3.13との互換性問題や、パッケージ間の依存関係競合がある
- 特に以下のパッケージで問題が発生：
  - `clip==1.0`: PyPIに存在しない → GitHubから直接インストール
  - `en-core-sci-lg==0.5.0`: spacyモデル、別途インストールが必要
  - `nmslib==2.1.1`: numpy要件が古い（<1.17）
  - `datasets==2.4.0` vs `nmslib`: numpy要件が競合

### 2. まだインストールしていないパッケージ
元のrequirements.txtから以下のパッケージは未インストール：
- 特殊なビルド要件があるもの（gptq等）
- 古すぎて互換性がないもの
- プロジェクトの動作に必須でない可能性のあるもの

必要に応じて個別にインストールしてください。

### 3. spacyモデルについて
`en-core-sci-lg`などのspacyモデルが必要な場合は別途インストール：
```bash
python -m spacy download en_core_web_sm
# または科学論文用モデル
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.0/en_core_sci_lg-0.5.0.tar.gz
```

### 4. CUDA/GPUサポート
現在のセットアップではCPU版がインストールされている可能性があります。
GPU環境で使用する場合は、PyTorchの公式手順に従ってCUDA対応版を再インストールしてください：
```bash
# PyTorch公式サイトで適切なコマンドを確認
# https://pytorch.org/
```

## トラブルシューティング

### モジュールが見つからない場合
プロジェクトの実行時に不足しているパッケージがある場合は：
```bash
uv pip install <package-name>
```

### バージョン互換性の問題が発生した場合
特定のバージョンが必要な場合：
```bash
uv pip install <package-name>==<version>
```

## プロジェクト実行

### トレーニング
```bash
source .venv/bin/activate
python train.py
```

### テスト
```bash
source .venv/bin/activate
python test.py
```

## データセットのセットアップ

### ✅ 完了済み（2026年3月30日）

事前抽出済みの特徴ファイルは`../SourceDatasets/SSG_VQA/`に存在していたため、シンボリックリンクでセットアップしました：

```bash
# 実行済みコマンド
mkdir -p data
cd data
ln -s ../../SourceDatasets/SSG_VQA/cropped_images .
ln -s ../../SourceDatasets/SSG_VQA/roi_yolo_coord .
ln -s ../../SourceDatasets/SSG_VQA/ssg-qa qa_txt

mkdir -p visual_feats
cd visual_feats
ln -s ../cropped_images .
ln -s ../roi_yolo_coord .
```

### 📊 データセット構成

以下のファイルが正しく配置されています：

1. **QA テキストファイル**: `data/qa_txt/`
   - 質問応答ペアのテキストファイル
   - 例: VID01に489ファイル

2. **Visual特徴量**: `data/visual_feats/cropped_images/`
   - ResNet18で抽出したビジュアル特徴量（HDF5形式）
   - 構造: `VID01/vqa/img_features/1x1/*.hdf5`

3. **ROI特徴量**: `data/visual_feats/roi_yolo_coord/`
   - YOLOで検出したROI領域の特徴量（HDF5形式）
   - 構造: `VID01/labels/vqa/img_features/roi/*.hdf5`

4. **Scene Graphs**: `scene_graph/`
   - 100,863個のJSONファイル（50ビデオ分）
   - このリポジトリに含まれている

### 検証コマンド

データセットのセットアップを確認：
```bash
python verify_dataset_setup.py
```

## 次のステップ
1. ~~データセットのダウンロード/配置~~ ✅ 完了
2. 設定ファイルの確認
3. トレーニングスクリプトの実行確認
4. 不足パッケージがあれば追加インストール

## トレーニング・テストの実行

### トレーニング開始
```bash
source .venv/bin/activate
python train.py --validate=False
```

### テスト実行
```bash
source .venv/bin/activate
python test.py --validate=True --checkpoint checkpoints/ssg-qa-net.pth.tar
```

---
**更新日**: 2026年3月30日（データセットセットアップ完了）
