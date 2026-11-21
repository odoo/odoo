import os, re

for f in os.listdir('views'):
    if f.endswith('.xml'):
        p = os.path.join('views', f)
        with open(p, 'r', encoding='utf-8') as fh:
            c = fh.read()
        for m in re.finditer(r'<menuitem[^>]*id="([^"]+)"[^>]*name="([^"]*Configuration[^"]*)"[^>]*>', c, re.I):
            print(f'{f}: {m.group(0)}')
        for m in re.finditer(r'<menuitem[^>]*name="([^"]*Configuration[^"]*)"[^>]*id="([^"]+)"[^>]*>', c, re.I):
            print(f'{f}: {m.group(0)}')
