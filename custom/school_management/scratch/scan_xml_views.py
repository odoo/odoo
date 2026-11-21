import os
import re

view_dirs = [
    r"C:\Odoo\odoo\custom\school_management\views",
    r"C:\Odoo\odoo\custom\school_management\wizard",
]

# Look for function calls in xml attributes
# e.g. .func() or func(...) inside domain, context, invisible, readonly, required, decoration-*, t-if, t-elif
func_pattern = re.compile(r'(\b\w+\.[a-zA-Z_]\w*\s*\(|\b(?:len|strftime|lower|upper|strip|split|filtered|mapped|sum|any|all|includes|indexOf|slice|startswith|endswith|weekday|today|now)\s*\()')

# Also check for regexes matching () inside attributes
attr_re = re.compile(r'(?:invisible|readonly|required|column_invisible|decoration-\w+|domain|context|t-if|t-elif)\s*=\s*"([^"]*)"')

for d in view_dirs:
    for fname in os.listdir(d):
        if not fname.endswith('.xml'):
            continue
        fpath = os.path.join(d, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        found = []
        for i, line in enumerate(lines, 1):
            for m in attr_re.finditer(line):
                val = m.group(1)
                if '(' in val and ')' in val:
                    # Check if it's not just a tuple like ('field', '=', value) or in ('a', 'b')
                    cleaned = re.sub(r"\('[^']*',\s*'[^']*',\s*[^)]*\)", "", val)
                    cleaned = re.sub(r"\bin\s*\([^)]*\)", "", cleaned)
                    cleaned = re.sub(r"\bnot\s+in\s*\([^)]*\)", "", cleaned)
                    if '(' in cleaned:
                        found.append((i, m.group(0)))
                # Also check func_pattern directly
                if func_pattern.search(val):
                    found.append((i, m.group(0)))
        if found:
            print(f"=== {fname} ===")
            seen = set()
            for ln, text in found:
                if (ln, text) not in seen:
                    seen.add((ln, text))
                    print(f"  Line {ln}: {text}")
