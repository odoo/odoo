import os

for root, dirs, files in os.walk(r"C:\Odoo\odoo\custom"):
    for f in files:
        p = os.path.join(root, f)
        try:
            with open(p, 'rb') as fp:
                data = fp.read()
                if b'name_khmer' in data:
                    print(f"Found in: {p}")
        except Exception:
            pass
