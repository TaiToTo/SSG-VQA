"""
複数シーングラフで改良版ロジックをテスト
"""
import json

samples = ['VID01_0', 'VID01_1', 'VID01_10', 'VID01_50', 'VID01_100']

# scene_graph_generation.py を import して使う
from scene_graph_generation import build_scene_graph

total_f1 = 0
count = 0

for sample in samples:
    try:
        with open(f'scene_graph/{sample}.json', 'r') as f:
            original = json.load(f)
    except FileNotFoundError:
        continue
    
    # 再生成
    scene = original['scenes'][0]
    info = original['info']
    regenerated_scene = build_scene_graph(scene, info)
    
    # 比較
    og_rels = original['scenes'][0]['relationships']
    cg_rels = regenerated_scene['relationships']
    
    print(f'\n{"="*70}')
    print(f'{sample}')
    print('='*70)
    
    sample_f1_sum = 0
    sample_count = 0
    
    for rel_type in ['above', 'below', 'left', 'right', 'within', 'grasp', 'horizontal']:
        if rel_type not in og_rels:
            continue
        
        matches = 0
        total_og = 0
        total_cg = 0
        
        for i in range(len(og_rels[rel_type])):
            og_set = set(og_rels[rel_type][i]) if i < len(og_rels[rel_type]) else set()
            cg_set = set(cg_rels[rel_type][i]) if i < len(cg_rels[rel_type]) else set()
            
            total_og += len(og_set)
            total_cg += len(cg_set)
            matches += len(og_set & cg_set)
        
        precision = matches / total_cg if total_cg > 0 else 0
        recall = matches / total_og if total_og > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f'{rel_type:12} | Prec:{precision:5.1%} Rec:{recall:5.1%} F1:{f1:5.1%} | OG:{total_og:2} CG:{total_cg:2} Match:{matches:2}')
        
        sample_f1_sum += f1
        sample_count += 1
    
    sample_avg_f1 = sample_f1_sum / sample_count if sample_count > 0 else 0
    print(f'{"平均 F1":12} | {sample_avg_f1:5.1%}')
    
    total_f1 += sample_avg_f1
    count += 1

print(f'\n{"="*70}')
print(f'全体平均 F1: {total_f1/count:.1%}')
print('='*70)
