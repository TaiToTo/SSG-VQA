from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import json


# ============================================================
# データ構造
# ============================================================
# JSON の object 要素をそのまま扱ってもよいですが、
# 実装を読みやすくするため dataclass に変換して扱います。
#
# 1つの ObjectNode は scene graph の「ノード」に対応します。
# bbox, component, type, center, location などを保持します。
# ============================================================

@dataclass
class ObjectNode:
    """
    1つの物体ノードを表すクラス。

    Attributes
    ----------
    bbox : Tuple[int, int, int, int]
        bounding box を (x1, y1, x2, y2) 形式で保持する。
    component : str
        物体名。例: 'liver', 'grasper', 'gallbladder'
    type : str
        'anatomy' または 'instrument'
    center : Tuple[float, float]
        bbox の中心座標。空間関係の計算に使う。
    location : str
        9分割グリッドなどで付けた位置ラベル。例: 'top-left'
    """
    bbox: Tuple[int, int, int, int]
    component: str
    type: str
    center: Tuple[float, float]
    location: str


# ============================================================
# 補助関数
# ============================================================

def parse_object(raw_obj: Dict[str, Any]) -> ObjectNode:
    """
    JSON 形式の object を ObjectNode に変換する。

    Parameters
    ----------
    raw_obj : dict
        入力 JSON 中の objects 配列の1要素。

    Returns
    -------
    ObjectNode
        dataclass 化された物体ノード。
    """
    return ObjectNode(
        bbox=tuple(raw_obj["bbox"]),
        component=raw_obj["component"],
        type=raw_obj["type"],
        center=tuple(raw_obj["center"]),
        location=raw_obj["location"],
    )


def normalize_name(name: str) -> str:
    """
    物体名比較のための簡単な正規化。

    triplet 側の名前と object 側の component 名が完全一致しない場合に備え、
    小文字化・前後空白除去をしておく。

    Notes
    -----
    実データでは、必要に応じて以下のような強化も考えられる。
    - ハイフン/アンダースコアの統一
    - 同義語辞書の適用
    - plural/singular の吸収
    """
    return name.strip().lower()


def find_object_indices_by_component(objects: List[ObjectNode], component_name: str) -> List[int]:
    """
    component 名に一致する object index をすべて返す。

    Parameters
    ----------
    objects : List[ObjectNode]
        シーン内物体一覧
    component_name : str
        探したい物体名。例: 'grasper'

    Returns
    -------
    List[int]
        一致した object index の一覧

    Notes
    -----
    同名の物体が複数ある可能性を考慮して list で返す。
    例えば grasper が2本見えているケースでは、複数 index が返る。
    """
    target = normalize_name(component_name)
    matched = []

    for idx, obj in enumerate(objects):
        if normalize_name(obj.component) == target:
            matched.append(idx)

    return matched


def bbox_area(bbox: Tuple[int, int, int, int]) -> int:
    """
    bbox の面積を返す。

    Notes
    -----
    within 判定を「完全包含」だけでなく「大部分が入っている」としたい場合、
    intersection 面積と組み合わせて使える。
    """
    x1, y1, x2, y2 = bbox
    return max(0, x2 - x1) * max(0, y2 - y1)


def intersection_area(
    bbox1: Tuple[int, int, int, int],
    bbox2: Tuple[int, int, int, int],
) -> int:
    """
    2つの bbox の交差面積を返す。

    Returns
    -------
    int
        交差領域の面積。重なりがなければ 0。
    """
    x1, y1, x2, y2 = bbox1
    X1, Y1, X2, Y2 = bbox2

    inter_x1 = max(x1, X1)
    inter_y1 = max(y1, Y1)
    inter_x2 = min(x2, X2)
    inter_y2 = min(y2, Y2)

    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0

    return (inter_x2 - inter_x1) * (inter_y2 - inter_y1)


def is_within(
    inner_bbox: Tuple[int, int, int, int],
    outer_bbox: Tuple[int, int, int, int],
    overlap_threshold: float = 0.9,
) -> bool:
    """
    bbox が別の bbox の「中にある」とみなせるかを判定する。

    Parameters
    ----------
    inner_bbox : tuple
        内側候補の bbox
    outer_bbox : tuple
        外側候補の bbox
    overlap_threshold : float
        inner_bbox のうち、outer_bbox に含まれている面積比の閾値。
        1.0 にすると完全包含のみ許可。
        0.9 程度にすると、少しはみ出したケースも許容できる。

    Returns
    -------
    bool
        inner_bbox が outer_bbox に十分含まれていれば True

    Notes
    -----
    JSON 例では grasper が gallbladder の中扱いになっており、
    実運用では厳密完全包含ではなく「ほぼ入っている」で判定している可能性もある。
    そのため、ここでは overlap ratio ベースにしている。

    ratio = intersection(inner, outer) / area(inner)
    が threshold 以上なら within とする。
    """
    inner_area = bbox_area(inner_bbox)
    if inner_area == 0:
        return False

    inter = intersection_area(inner_bbox, outer_bbox)
    ratio = inter / inner_area
    return ratio >= overlap_threshold


def has_overlap(
    bbox1: Tuple[int, int, int, int],
    bbox2: Tuple[int, int, int, int],
    min_overlap_ratio: float = 0.20,
) -> bool:
    """
    2つのbboxが重なっているかを判定（双方向、完全包含優先）。
    
    実データ分析の結果:
    - 81.8%が完全包含（どちらか一方が他方に完全に含まれる）
    - anatomy同士の最小overlap_max = 20%
    - instrument→anatomyの最小overlap_max = 82.4%
    
    Parameters
    ----------
    bbox1, bbox2 : tuple
        判定対象の2つのbbox
    min_overlap_ratio : float
        最小overlap比率（データ分析より20%）
    
    Returns
    -------
    bool
        完全包含 OR overlap_max >= 20% なら True
    
    Notes
    -----
    実データの例：
    - liver → gallbladder: overlap_max=100% (gallbladder完全にliver内)
    - gut → omentum: overlap_max=20% (部分的重なり)
    """
    x1, y1, x2, y2 = bbox1
    X1, Y1, X2, Y2 = bbox2
    
    area1 = bbox_area(bbox1)
    area2 = bbox_area(bbox2)
    
    if area1 == 0 or area2 == 0:
        return False
    
    # 完全包含チェック（優先）
    bbox1_in_bbox2 = (x1 >= X1 and y1 >= Y1 and x2 <= X2 and y2 <= Y2)
    bbox2_in_bbox1 = (X1 >= x1 and Y1 >= y1 and X2 <= x2 and Y2 <= y2)
    
    if bbox1_in_bbox2 or bbox2_in_bbox1:
        return True
    
    # overlap_max チェック
    inter = intersection_area(bbox1, bbox2)
    
    ratio1 = inter / area1
    ratio2 = inter / area2
    overlap_max = max(ratio1, ratio2)
    
    return overlap_max >= min_overlap_ratio



def is_horizontal(
    center_a: Tuple[float, float],
    center_b: Tuple[float, float],
    y_threshold: float = 40.0,
    min_x_distance: float = 40.0,
) -> bool:
    """
    2つのオブジェクトが「水平関係」にあるかを判定する。
    
    実データ分析の結果:
    - y差: 0.0～40.5px（最大40.5px）
    - x差: 41.5～151.5px（最小41.5px、平均94.5px）
    
    Parameters
    ----------
    center_a, center_b : tuple
        各オブジェクトの中心座標 (x, y)
    y_threshold : float
        許容するy座標の差分（データ分析より40px）
    min_x_distance : float
        最小x距離（データ分析より40px）

    Returns
    -------
    bool
        y差 <= 40px AND x差 >= 40px なら True
        
    Notes
    -----
    x差の条件がないと、垂直に並んでいるペアも誤検出してしまう。
    horizontal関係は「横に並んでいる」という意味なので、
    十分なx距離が必要。
    """
    xa, ya = center_a
    xb, yb = center_b
    
    y_diff = abs(ya - yb)
    x_diff = abs(xa - xb)
    
    return y_diff <= y_threshold and x_diff >= min_x_distance


# ============================================================
# 関係グラフ構築本体
# ============================================================

def build_relationships(
    objects: List[ObjectNode],
    triplets: List[str],
    horizontal_y_threshold: float = 40.0,
    horizontal_min_x_distance: float = 40.0,
    within_overlap_threshold: float = 0.20,
    min_spatial_distance: float = 40.0,
) -> Dict[str, List[List[int]]]:
    """
    objects と triplets から relationship 辞書を構築する。

    Parameters
    ----------
    objects : List[ObjectNode]
        scene 内の全物体
    triplets : List[str]
        action relation を表す文字列の配列
        例: ["grasper,grasp,gallbladder"]
    horizontal_y_threshold : float
        horizontal 判定で使う y差の閾値（データ分析より40px）
    horizontal_min_x_distance : float
        horizontal 判定で使う最小x距離（データ分析より40px）
    within_overlap_threshold : float
        within 判定で使う overlap ratio の閾値（データ分析より20%）

    Returns
    -------
    Dict[str, List[List[int]]]
        relation 名 -> 各 object index から到達可能な相手 index 一覧

        例:
        {
            "left":  [ [...], [...], ... ],
            "right": [ [...], [...], ... ],
            ...
        }

    設計意図
    --------
    出力形式は、ユーザーが提示した JSON に合わせている。
    つまり object i に対して、relation r の相手先 index 群を
    relationships[r][i] に格納する。

    例:
    relationships["grasp"][5] = [4]
    は
    object 5 --grasp--> object 4
    を意味する。
    """
    num_objects = len(objects)

    # --------------------------------------------------------
    # relation ごとの adjacency list を初期化する。
    # 各 relation は「長さ num_objects の配列」を持ち、
    # その各要素は「相手 object index の list」である。
    # --------------------------------------------------------
    relationships: Dict[str, List[List[int]]] = {
        "above": [[] for _ in range(num_objects)],
        "below": [[] for _ in range(num_objects)],
        "left": [[] for _ in range(num_objects)],
        "right": [[] for _ in range(num_objects)],
        "within": [[] for _ in range(num_objects)],
        "horizontal": [[] for _ in range(num_objects)],
    }

    # --------------------------------------------------------
    # 1. 空間関係 (spatial relations) を計算する
    # --------------------------------------------------------
    # 論文本文では spatial relation は centroid を比較して計算するとある。
    # したがって、各物体ペア (i, j) について center を比較し、
    # left/right/above/below を埋める。
    #
    # ここでは directed relation として保存する。
    # 例えば x_j < x_i なら、「i から見て j は left」に入れる。
    # --------------------------------------------------------
    for i in range(num_objects):
        for j in range(num_objects):
            if i == j:
                # 自分自身との関係は作らない
                continue

            xi, yi = objects[i].center
            xj, yj = objects[j].center

            # ---- left / right ----
            # object j が object i より左にあれば left[i] に j を入れる。
            # ただし、x差が min_spatial_distance 以上の場合のみ。
            x_diff = abs(xj - xi)
            if x_diff >= min_spatial_distance:
                if xj < xi:
                    relationships["left"][i].append(j)
                elif xj > xi:
                    relationships["right"][i].append(j)

            # ---- above / below ----
            # 画像座標系では y が小さいほど「上」。
            # ただし、y差が min_spatial_distance 以上の場合のみ。
            y_diff = abs(yj - yi)
            if y_diff >= min_spatial_distance:
                if yj < yi:
                    relationships["above"][i].append(j)
                elif yj > yi:
                    relationships["below"][i].append(j)

            # ---- horizontal ----
            # 「水平関係」にある場合に relation を付ける。
            # 実データ分析より: y差 <= 40px AND x差 >= 40px
            if is_horizontal(
                objects[i].center,
                objects[j].center,
                y_threshold=horizontal_y_threshold,
                min_x_distance=horizontal_min_x_distance,
            ):
                relationships["horizontal"][i].append(j)

            # ---- within ----
            # object i と object j が重なっている（接触している）場合、
            # within[i].append(j) を追加する。
            # 双方向の overlap 判定を使用（どちらか一方でも閾値以上）
            if has_overlap(
                objects[i].bbox,
                objects[j].bbox,
                min_overlap_ratio=within_overlap_threshold,
            ):
                relationships["within"][i].append(j)

    # --------------------------------------------------------
    # 2. action relation を triplet annotation から追加する
    # --------------------------------------------------------
    # triplet の形式は "instrument,verb,target" を想定する。
    #
    # 例:
    #   "grasper,grasp,gallbladder"
    #
    # これを parse して、
    #   grasper の index -> grasp -> gallbladder の index
    # を relationships に追加する。
    #
    # relation 名（verb）は可変なので、初見のものはここで新規作成する。
    # --------------------------------------------------------
    for triplet_str in triplets:
        parts = [p.strip() for p in triplet_str.split(",")]

        # triplet の形式がおかしい場合は無視する。
        # 実運用なら logger.warning を出してもよい。
        if len(parts) != 3:
            continue

        subject_name, relation_name, object_name = parts

        # relation 名がまだなければ初期化
        if relation_name not in relationships:
            relationships[relation_name] = [[] for _ in range(num_objects)]

        # 同名 object が複数あるケースに備え、複数 index を許容する。
        subject_indices = find_object_indices_by_component(objects, subject_name)
        object_indices = find_object_indices_by_component(objects, object_name)

        # subject または object が見つからなければ、その triplet は構築不能。
        if not subject_indices or not object_indices:
            continue

        # 通常は instrument 1つ -> anatomy 1つ だが、
        # 同名が複数見つかった場合は全組み合わせで relation を張る。
        for subj_idx in subject_indices:
            for obj_idx in object_indices:
                if obj_idx not in relationships[relation_name][subj_idx]:
                    relationships[relation_name][subj_idx].append(obj_idx)

    # --------------------------------------------------------
    # 3. 出力を安定化するため、各隣接リストをソートしておく
    # --------------------------------------------------------
    # テスト比較や JSON diff を見やすくするために有効。
    # --------------------------------------------------------
    for rel_name, adjacency in relationships.items():
        for neighbors in adjacency:
            neighbors.sort()

    return relationships


# ============================================================
# scene 1件を処理する関数
# ============================================================

def build_scene_graph(scene: Dict[str, Any], info: Dict[str, Any]) -> Dict[str, Any]:
    """
    入力 scene と info から relationships を再構築し、
    scene graph 形式の dict を返す。

    Parameters
    ----------
    scene : dict
        1シーン分の JSON データ。objects, image_filename などを含む。
    info : dict
        JSON の info セクション。triplet などを含む。

    Returns
    -------
    dict
        relationships を再計算して入れた scene 辞書
    """
    objects = [parse_object(obj) for obj in scene["objects"]]
    triplets = info.get("triplet", [])

    relationships = build_relationships(
        objects=objects,
        triplets=triplets,
        horizontal_y_threshold=40.0,
        horizontal_min_x_distance=40.0,
        within_overlap_threshold=0.20,
        min_spatial_distance=40.0,
    )

    # 元の object 情報を JSON に戻しやすい形で再構築する
    output_objects = []
    for obj in objects:
        output_objects.append({
            "bbox": list(obj.bbox),
            "component": obj.component,
            "type": obj.type,
            "center": list(obj.center),
            "location": obj.location,
        })

    return {
        "objects": output_objects,
        "image_filename": scene.get("image_filename"),
        "relationships": relationships,
    }


# ============================================================
# 動作例
# ============================================================
# ユーザーが提示した例をそのまま input_data に入れて試す。
# 実行すると、relationships が再計算されて表示される。
#
# 注意:
# - horizontal, within のルールは論文本文で厳密定義されていないため、
#   あなたの JSON と完全一致しないケースはありうる。
# - left/right/above/below と triplet 由来 action はかなり素直に再現できる。
# ============================================================

if __name__ == "__main__":
    input_data = {
        "scenes": [
            {
                "objects": [
                    {
                        "bbox": [20, 0, 166, 239],
                        "component": "abdominal_wall_cavity",
                        "type": "anatomy",
                        "center": [93.0, 119.5],
                        "location": "top-left"
                    },
                    {
                        "bbox": [88, 0, 399, 239],
                        "component": "liver",
                        "type": "anatomy",
                        "center": [243.5, 119.5],
                        "location": "top-mid"
                    },
                    {
                        "bbox": [290, 234, 367, 239],
                        "component": "gut",
                        "type": "anatomy",
                        "center": [328.5, 236.5],
                        "location": "bottom-right"
                    },
                    {
                        "bbox": [278, 168, 388, 235],
                        "component": "omentum",
                        "type": "anatomy",
                        "center": [333.0, 201.5],
                        "location": "bottom-right"
                    },
                    {
                        "bbox": [153, 9, 289, 220],
                        "component": "gallbladder",
                        "type": "anatomy",
                        "center": [221.0, 114.5],
                        "location": "top-mid"
                    },
                    {
                        "bbox": [198, 3, 279, 37],
                        "component": "grasper",
                        "type": "instrument",
                        "center": [238.5, 20.0],
                        "location": "top-mid"
                    }
                ],
                "image_filename": "VID01_0"
            }
        ],
        "info": {
            "split": "new",
            "image_index": 0,
            "image_filename": ["VID01_0"],
            "triplet": ["grasper,grasp,gallbladder"]
        }
    }

    result = {
        "scenes": [
            build_scene_graph(scene, input_data["info"])
            for scene in input_data["scenes"]
        ],
        "info": input_data["info"]
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))