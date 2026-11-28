path = 'custom/school_management/scratch/test_policy_verification.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '"title": "Policy Test Hidden Followup",',
    '"title": "Policy Test Hidden Followup",\n        "advisor_id": teacher_rec.id,'
)

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print("Updated line 258 in test script")
