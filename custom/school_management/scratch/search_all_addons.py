import os

paths = [
    r"C:\Odoo\odoo\addons",
    r"C:\Odoo\odoo\odoo\addons",
    r"C:\Odoo\odoo\custom",
    r"C:\Users\Rith2\AppData\Local\OpenERP S.A.\Odoo\addons\19.0",
]

for base in paths:
    if not os.path.exists(base):
        continue
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(root, f)
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                        content = fp.read()
                        if 'name_khmer' in content:
                            print(f"Found in {p}")
                except Exception as e:
                    pass
