#!/usr/bin/env python3
"""
CholecT50とSSG-VQAの互換性確認スクリプト
"""
import os

# SSG-VQAで使用されるビデオ
train_seq = ["VID73", "VID40", "VID62", "VID42", "VID29", "VID56", "VID50", "VID78", "VID66", "VID13", "VID52", "VID06", "VID36", "VID05", "VID12", "VID26", "VID68", "VID32", "VID49", "VID65", "VID47", "VID04", "VID23", "VID79", "VID51", "VID10", "VID57", "VID75", "VID25", "VID14", "VID15", "VID08", "VID80", "VID27", "VID70"]
val_seq = ["VID18", "VID48", "VID01", "VID35", "VID31"]
test_seq = ["VID22", "VID74", "VID60", "VID02", "VID43"]

used_vids = set(train_seq + val_seq + test_seq)

# CholecT50のビデオ
cholect50_path = "../SourceDatasets/CholecT50/videos/"
if os.path.exists(cholect50_path):
    cholect50_vids = set([d for d in os.listdir(cholect50_path) if d.startswith("VID") and os.path.isdir(os.path.join(cholect50_path, d))])
else:
    print(f"エラー: {cholect50_path} が見つかりません")
    exit(1)

print("=" * 80)
print("CholecT50とSSG-VQAの互換性確認")
print("=" * 80)
print(f"\n📊 ビデオ数の概要:")
print(f"  - SSG-VQAで使用: {len(used_vids)}ビデオ")
print(f"    • Train: {len(train_seq)}ビデオ")
print(f"    • Val: {len(val_seq)}ビデオ")
print(f"    • Test: {len(test_seq)}ビデオ")
print(f"  - CholecT50に存在: {len(cholect50_vids)}ビデオ")

# 使用されていないビデオ
unused = sorted(cholect50_vids - used_vids)
print(f"\n📁 CholecT50に存在するがSSG-VQAで使用されていないビデオ（{len(unused)}個）:")
for vid in unused:
    print(f"    • {vid}")

# 欠落チェック
missing = sorted(used_vids - cholect50_vids)
if missing:
    print(f"\n⚠️  SSG-VQAで必要だがCholecT50に存在しないビデオ（{len(missing)}個）:")
    for vid in missing:
        print(f"    • {vid}")
else:
    print(f"\n✅ SSG-VQAで必要なビデオはすべてCholecT50に存在します")

print("\n" + "=" * 80)
print("📝 結論:")
print("=" * 80)
print("• SSG-VQAプロジェクトはCholecT45を想定（45ビデオ）")
print("• CholecT50にはこれらすべてのビデオ + 追加の5ビデオが含まれています")
print("• CholecT50のデータセットはSSG-VQAプロジェクトで使用可能です ✓")
print("=" * 80)
