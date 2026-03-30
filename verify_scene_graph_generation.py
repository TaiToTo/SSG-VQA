"""
シーングラフ生成プロセスの検証スクリプト

既存のシーングラフJSONからBBox座標を読み取り、
空間・動作関係を再計算して元のデータと比較する
"""
import json
import numpy as np
from typing import List, Dict, Tuple


def calculate_iou(bbox1: List[float], bbox2: List[float]) -> float:
    """IoU（Intersection over Union）を計算"""
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2
    
    # 交差領域
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i < x1_i or y2_i < y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0


def compute_vertical_relationships(objects: List[Dict]) -> Tuple[List[List[int]], List[List[int]]]:
    """上下関係を計算
    
    above[i] = iの上にあるオブジェクトのリスト (j's y < i's y)
    below[i] = iの下にあるオブジェクトのリスト (j's y > i's y)
    """
    n = len(objects)
    above = [[] for _ in range(n)]
    below = [[] for _ in range(n)]
    
    threshold = 10  # ピクセル単位の閾値
    
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            
            y_i = objects[i]['center'][1]
            y_j = objects[j]['center'][1]
            
            if y_j < y_i - threshold:
                # jはiの上にある (jのy座標がiより小さい)
                above[i].append(j)
                below[j].append(i)
    
    return above, below


def compute_horizontal_position_relationships(objects: List[Dict]) -> Tuple[List[List[int]], List[List[int]]]:
    """左右関係を計算
    
    left[i] = iの左にあるオブジェクトのリスト (j's x < i's x)
    right[i] = iの右にあるオブジェクトのリスト (j's x > i's x)
    """
    n = len(objects)
    left = [[] for _ in range(n)]
    right = [[] for _ in range(n)]
    
    threshold = 10
    
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            
            x_i = objects[i]['center'][0]
            x_j = objects[j]['center'][0]
            
            if x_j < x_i - threshold:
                # jはiの左にある (jのx座標がiより小さい)
                left[i].append(j)
                right[j].append(i)
    
    return left, right


def compute_containment_relationships(objects: List[Dict]) -> List[List[int]]:
    """包含関係を計算
    
    within[i] = iが含んでいるオブジェクトのリスト (i contains j)
    """
    n = len(objects)
    within = [[] for _ in range(n)]
    
    for i in range(n):
        bbox_i = objects[i]['bbox']
        x1_i, y1_i, x2_i, y2_i = bbox_i
        
        for j in range(n):
            if i == j:
                continue
            
            bbox_j = objects[j]['bbox']
            x1_j, y1_j, x2_j, y2_j = bbox_j
            
            # jがiに完全に含まれるか (i contains j)
            if (x1_i <= x1_j and y1_i <= y1_j and 
                x2_j <= x2_i and y2_j <= y2_i):
                within[i].append(j)
            else:
                # IoU による包含判定
                iou = calculate_iou(bbox_i, bbox_j)
                if iou > 0.7:
                    area_i = (x2_i - x1_i) * (y2_i - y1_i)
                    area_j = (x2_j - x1_j) * (y2_j - y1_j)
                    # iがjより大きい場合、iがjを含む
                    if area_i > area_j * 1.5:
                        within[i].append(j)
    
    return within


def is_completely_contained(bbox1: List[float], bbox2: List[float]) -> bool:
    """bbox1がbbox2に完全に含まれているか"""
    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2
    
    return (x1_2 <= x1_1 and y1_2 <= y1_1 and 
            x2_1 <= x2_2 and y2_1 <= y2_2)


def detect_grasp_relationships(objects: List[Dict]) -> List[List[int]]:
    """把持関係を検出"""
    n = len(objects)
    grasp = [[] for _ in range(n)]
    
    # 把持可能な器具
    grasping_instruments = {'grasper', 'clipper', 'scissors'}
    
    # 把持可能な臓器
    graspable_anatomies = {
        'gallbladder', 'liver', 'omentum', 'gut', 
        'cystic_duct', 'cystic_artery', 'peritoneum',
        'cystic_plate', 'abdominal_wall_cavity'
    }
    
    for i in range(n):
        if objects[i]['component'] not in grasping_instruments:
            continue
        
        bbox_i = objects[i]['bbox']
        x1_i, y1_i, x2_i, y2_i = bbox_i
        
        for j in range(n):
            if i == j:
                continue
            
            if objects[j]['component'] not in graspable_anatomies:
                continue
            
            bbox_j = objects[j]['bbox']
            x1_j, y1_j, x2_j, y2_j = bbox_j
            
            # IoUを計算
            iou = calculate_iou(bbox_i, bbox_j)
            
            # IoUが閾値以上なら把持関係あり（より低い閾値を使用）
            if iou > 0.1:
                # 器具が臓器の上部付近にあるか確認（把持は通常上から）
                instrument_center_y = objects[i]['center'][1]
                anatomy_center_y = objects[j]['center'][1]
                
                # 器具が臓器より上または同じ高さにある
                if instrument_center_y <= anatomy_center_y + 50:
                    grasp[i].append(j)
            else:
                # IoUが小さくても、bbox が接触していれば把持と判定
                # x方向の重なりチェック
                x_overlap = not (x2_i < x1_j or x2_j < x1_i)
                # y方向の近接チェック（器具の下端と臓器の上端が近い）
                y_close = abs(y2_i - y1_j) < 30 or abs(y1_i - y1_j) < 100
                
                if x_overlap and y_close:
                    grasp[i].append(j)
    
    return grasp


def detect_horizontal_relationships(objects: List[Dict]) -> List[List[int]]:
    """水平配置関係を検出"""
    n = len(objects)
    horizontal = [[] for _ in range(n)]
    
    y_threshold = 20  # y座標の差の閾値
    
    for i in range(n):
        y_i = objects[i]['center'][1]
        x_i = objects[i]['center'][0]
        
        for j in range(n):
            if i == j:
                continue
            
            y_j = objects[j]['center'][1]
            x_j = objects[j]['center'][0]
            
            # y座標がほぼ同じ
            if abs(y_i - y_j) < y_threshold:
                # x座標に適度な距離がある
                if abs(x_i - x_j) > 50:
                    horizontal[i].append(j)
    
    return horizontal


def compare_relationships(original: List[List[int]], computed: List[List[int]], rel_name: str) -> Dict:
    """関係性の比較"""
    matches = 0
    total_original = 0
    total_computed = 0
    
    for i in range(len(original)):
        orig_set = set(original[i])
        comp_set = set(computed[i])
        
        total_original += len(orig_set)
        total_computed += len(comp_set)
        matches += len(orig_set & comp_set)
    
    precision = matches / total_computed if total_computed > 0 else 0
    recall = matches / total_original if total_original > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        'name': rel_name,
        'matches': matches,
        'original_total': total_original,
        'computed_total': total_computed,
        'precision': precision,
        'recall': recall,
        'f1_score': f1
    }


def verify_scene_graph(scene_graph_path: str) -> Dict:
    """
    シーングラフJSONを検証
    
    Args:
        scene_graph_path: シーングラフJSONファイルのパス
    
    Returns:
        検証結果の辞書
    """
    # JSONを読み込み
    with open(scene_graph_path, 'r') as f:
        scene_graph = json.load(f)
    
    scene = scene_graph['scenes'][0]
    objects = scene['objects']
    original_rels = scene['relationships']
    
    print(f"\n{'='*60}")
    print(f"検証対象: {scene_graph_path}")
    print(f"{'='*60}")
    print(f"オブジェクト数: {len(objects)}")
    print(f"\nオブジェクト一覧:")
    for i, obj in enumerate(objects):
        print(f"  [{i}] {obj['component']} ({obj['type']}) at {obj['center']}")
    
    # 関係性を再計算
    print(f"\n{'='*60}")
    print("関係性を再計算中...")
    print(f"{'='*60}")
    
    above, below = compute_vertical_relationships(objects)
    left, right = compute_horizontal_position_relationships(objects)
    within = compute_containment_relationships(objects)
    grasp = detect_grasp_relationships(objects)
    horizontal = detect_horizontal_relationships(objects)
    
    computed_rels = {
        'above': above,
        'below': below,
        'left': left,
        'right': right,
        'within': within,
        'grasp': grasp,
        'horizontal': horizontal
    }
    
    # 比較
    print(f"\n{'='*60}")
    print("元データと計算結果の比較")
    print(f"{'='*60}")
    
    results = {}
    for rel_name in ['above', 'below', 'left', 'right', 'within', 'grasp', 'horizontal']:
        result = compare_relationships(
            original_rels[rel_name],
            computed_rels[rel_name],
            rel_name
        )
        results[rel_name] = result
        
        print(f"\n{rel_name.upper()}:")
        print(f"  元データ: {result['original_total']} 個の関係")
        print(f"  計算結果: {result['computed_total']} 個の関係")
        print(f"  一致数: {result['matches']}")
        print(f"  Precision: {result['precision']:.2%}")
        print(f"  Recall: {result['recall']:.2%}")
        print(f"  F1 Score: {result['f1_score']:.2%}")
    
    # 詳細な不一致の表示
    print(f"\n{'='*60}")
    print("詳細な不一致箇所")
    print(f"{'='*60}")
    
    for rel_name in ['above', 'below', 'left', 'right', 'within', 'grasp', 'horizontal']:
        print(f"\n{rel_name.upper()}:")
        for i in range(len(objects)):
            orig_set = set(original_rels[rel_name][i])
            comp_set = set(computed_rels[rel_name][i])
            
            missing = orig_set - comp_set
            extra = comp_set - orig_set
            
            if missing or extra:
                print(f"  [{i}] {objects[i]['component']}:")
                if missing:
                    missing_names = [f"{j}:{objects[j]['component']}" for j in missing]
                    print(f"    欠落: {missing_names}")
                if extra:
                    extra_names = [f"{j}:{objects[j]['component']}" for j in extra]
                    print(f"    追加: {extra_names}")
    
    # 総合評価
    print(f"\n{'='*60}")
    print("総合評価")
    print(f"{'='*60}")
    
    avg_precision = np.mean([r['precision'] for r in results.values()])
    avg_recall = np.mean([r['recall'] for r in results.values()])
    avg_f1 = np.mean([r['f1_score'] for r in results.values()])
    
    print(f"平均 Precision: {avg_precision:.2%}")
    print(f"平均 Recall: {avg_recall:.2%}")
    print(f"平均 F1 Score: {avg_f1:.2%}")
    
    return {
        'scene_graph_path': scene_graph_path,
        'num_objects': len(objects),
        'relationships': results,
        'avg_precision': avg_precision,
        'avg_recall': avg_recall,
        'avg_f1': avg_f1
    }


if __name__ == "__main__":
    # VID01_0.jsonを検証
    result = verify_scene_graph('scene_graph/VID01_0.json')
    
    print(f"\n{'='*60}")
    print("検証完了")
    print(f"{'='*60}")
    
    if result['avg_f1'] > 0.9:
        print("✅ 高い一致率！アルゴリズムは正確です。")
    elif result['avg_f1'] > 0.7:
        print("⚠️  まずまずの一致率。閾値の調整が必要かもしれません。")
    else:
        print("❌ 一致率が低い。アルゴリズムの見直しが必要です。")
