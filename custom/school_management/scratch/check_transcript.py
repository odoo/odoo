import json

lines_to_check = [28, 70, 90, 98, 100, 513, 515, 517, 518, 519, 521]
with open('C:/Users/Rith2/.gemini/antigravity-acp/brain/78b4311f-52e2-48ba-b5c3-a1f375fd9f6c/.system_generated/logs/transcript.jsonl', 'r', encoding='utf-8') as f:
    for idx, l in enumerate(f):
        if idx in lines_to_check:
            d = json.loads(l)
            print(f"=== Line {idx} ({d.get('type')}, {d.get('source')}) ===")
            if 'content' in d:
                print(str(d['content'])[:300])
