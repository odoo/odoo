import os

search_dir = r"C:\Odoo\odoo\custom"
target = "name_khmer"

for root, dirs, files in os.walk(search_dir):
    for f in files:
        if f.endswith(('.py', '.xml', '.js', '.csv', '.json')):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    for i, line in enumerate(fp, 1):
                        if target in line:
                            print(f"{path}:{i}: {line.strip()}")
            except Exception as e:
                pass
