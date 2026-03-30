import json

# 読み込み
with open('chatgpt_output.json', 'r') as f:
    chatgpt = json.load(f)

with open('scene_graph/VID01_0.json', 'r') as f:
    original = json.load(f)

# 関係性を比較
rels_cg = chatgpt['scenes'][0]['relationships']
rels_og = original['scenes'][0]['relationships']

print('📊 ChatGPT実装の精度評価')
print('='*70)

total_f1 = 0
count = 0

for rel_type in ['above', 'below', 'left', 'right', 'within', 'grasp', 'horizontal']:
    if rel_type not in rels_og:
        continue
        
    matches = 0
    total_og = 0
    total_cg = 0
    
    for i in range(len(rels_og[rel_type])):
        og_set = set(rels_og[rel_type][i]) if i < len(rels_og[rel_type]) else set()
        cg_set = set(rels_cg[rel_type][i]) if i < len(rels_cg[rel_type]) else set()
        
        total_og += len(og_set)
        total_cg += len(cg_set)
        matches += len(og_set & cg_set)
    
    precision = matches / total_cg if total_cg > 0 else 0
    recall = matches / total_og if total_og > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f'{rel_type:12} | オリジナル:{total_og:2} ChatGPT:{total_cg:2} | 一致:{matches:2} | Precision:{precision:.1%} Recall:{recall:.1%} F1:{f1:.1%}')
    
    total_f1 += f1
    count += 1

print('='*70)
print(f'平均 F1スコア: {total_f1/count:.1%}')
