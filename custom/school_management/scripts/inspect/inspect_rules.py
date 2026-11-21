import re

with open('security/record_rules.xml', 'r', encoding='utf-8') as f:
    content = f.read()

models_to_check = [
    'university.assignment',
    'university.assignment.submission',
    'university.class.section',
    'university.attendance',
    'university.curriculum',
    'university.curriculum.line',
    'university.fee',
    'university.report.card'
]

records = re.findall(r'<record id="([^"]+)" model="ir\.rule">([\s\S]*?)</record>', content)
print(f"Total rules: {len(records)}")
for rec_id, body in records:
    for m in models_to_check:
        if f'ref="model_{m.replace(".", "_")}"' in body:
            # find group and domain_force
            group = re.search(r'name="groups" ref="([^"]+)"', body)
            domain = re.search(r'name="domain_force">([\s\S]*?)</field>', body)
            grp_str = group.group(1) if group else 'GLOBAL'
            dom_str = domain.group(1).strip() if domain else ''
            print(f"Rule: {rec_id} | Model: {m} | Group: {grp_str}")
            print(f"   Domain: {dom_str}\n")
