import re

with open('security/record_rules.xml', 'r', encoding='utf-8') as f:
    text = f.read()

rules = ['rule_student_own_assignments', 'rule_student_own_class_sections', 'rule_student_own_submissions', 'rule_student_own_attendance']
for r in rules:
    m = re.search(r'<record id="' + r + r'"[\s\S]*?</record>', text)
    if m:
        print(f"=== {r} ===")
        print(m.group(0))
