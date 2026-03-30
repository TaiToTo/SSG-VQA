# SSG-VQAプロジェクト セットアップ記録（2026年3月30日）

## 実施した作業

### 1. 環境セットアップ
- **Python環境**: uvを使用してPython 3.13.3の仮想環境を作成
- **依存パッケージ**: 最新版でインストール
  - PyTorch 2.11.0
  - Transformers 5.4.0
  - その他主要パッケージ（詳細は[SETUP_NOTES.md](SETUP_NOTES.md)参照）

**注意**: 元のrequirements.txtは古いバージョン指定で互換性問題があったため、主要パッケージを最新版でインストール

### 2. CholecT45/T50互換性確認
- **確認結果**: CholecT50はSSG-VQAで完全に使用可能
- **詳細**: [CHOLECT50_COMPATIBILITY.md](CHOLECT50_COMPATIBILITY.md)参照
- **理由**: CholecT50はCholecT45のスーパーセット（45本 + 追加5本）

### 3. データセット配置
既存の`../SourceDatasets/SSG_VQA/`のデータをシンボリックリンクで配置：

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

**配置済みデータ**:
- ✅ QAテキストファイル（質問応答ペア）
- ✅ Visual特徴量（ResNet18抽出、HDF5形式）
- ✅ ROI特徴量（YOLO検出、HDF5形式）
- ✅ Scene Graphs（100,863個のJSON、このリポジトリに含まれる）

### 4. 検証スクリプト作成
以下のスクリプトを作成して動作確認：

- **check_dataset_compatibility.py**: CholecT50との互換性確認
- **check_file_structure.py**: ファイル構造の説明
- **verify_dataset_setup.py**: セットアップ状態の確認

## 作成・更新したファイル

### 新規作成
1. `requirements.txt` - pipパッケージリスト（environment.ymlから抽出）
2. `SETUP_NOTES.md` - 環境セットアップの詳細記録
3. `CHOLECT50_COMPATIBILITY.md` - データセット互換性の確認結果
4. `check_dataset_compatibility.py` - 互換性確認スクリプト
5. `check_file_structure.py` - 構造説明スクリプト
6. `verify_dataset_setup.py` - セットアップ検証スクリプト

### 複製
- `CHOLECT50_COMPATIBILITY.md` → `../SourceDatasets/` にも配置

### ディレクトリ構造
```
SSG-VQA/
├── .venv/                          # Python 3.13仮想環境
├── data/                           # データディレクトリ（新規作成）
│   ├── cropped_images -> ../../SourceDatasets/SSG_VQA/cropped_images
│   ├── roi_yolo_coord -> ../../SourceDatasets/SSG_VQA/roi_yolo_coord
│   ├── qa_txt -> ../../SourceDatasets/SSG_VQA/ssg-qa
│   └── visual_feats/
│       ├── cropped_images -> ../cropped_images
│       └── roi_yolo_coord -> ../roi_yolo_coord
├── scene_graph/                    # 既存（100,863 JSONファイル）
├── models/
├── utils/
├── SETUP_NOTES.md                  # セットアップ詳細
├── CHOLECT50_COMPATIBILITY.md      # 互換性確認
├── check_dataset_compatibility.py
├── check_file_structure.py
├── verify_dataset_setup.py
├── train.py
└── test.py
```

## 現在の状態

### ✅ 完了
- Python環境構築（uv + Python 3.13）
- 主要パッケージインストール
- データセット互換性確認
- データディレクトリ配置・検証

### 📋 次のステップ
1. 実行前の最終確認:
   ```bash
   source .venv/bin/activate
   python verify_dataset_setup.py
   ```

2. トレーニング開始:
   ```bash
   python train.py --validate=False
   ```

3. モデルウェイトダウンロード（テスト実行時）:
   ```bash
   mkdir -p checkpoints
   wget https://s3.unistra.fr/camma_public/github/ssg-qa/ssg-qa-net.pth.tar -P checkpoints/
   python test.py --validate=True --checkpoint checkpoints/ssg-qa-net.pth.tar
   ```

## 注意事項

### パッケージバージョン
- 元のrequirements.txtは2022年頃のバージョン
- Python 3.13との互換性を考慮して最新版でインストール
- 動作確認しながら必要に応じて追加インストール

### GPU/CUDA
- 現在のセットアップはCPU版
- GPU環境で実行する場合はPyTorch公式サイトからCUDA版を再インストール

### データセット
- CholecT50を使用（CholecT45互換）
- 特徴量ファイルは既に`../SourceDatasets/SSG_VQA/`に存在
- 生画像は`../SourceDatasets/CholecT50/videos/`に存在（参考用）

---
**作成日**: 2026年3月30日  
**Python**: 3.13.3  
**パッケージマネージャ**: uv 0.7.2
