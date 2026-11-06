import json

with open('C:/Users/Rith2/.gemini/antigravity-acp/brain/78b4311f-52e2-48ba-b5c3-a1f375fd9f6c/.system_generated/logs/transcript.jsonl', 'r', encoding='utf-8') as f:
    for idx, l in enumerate(f):
        d = json.loads(l)
        if d.get("type") == "USER_INPUT":
            print(f"=== User Step {idx} ===")
            print(d.get("content"))
