path = 'custom/school_management/scratch/test_policy_verification.py'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace(
    '"action_type": "tutoring",',
    '"advisor_id": teacher_rec.id, "action_type": "tutoring",'
)
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
print('Updated test script')
