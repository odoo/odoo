import glob
from lxml import etree

valid_aria_attrs = {'title', 'aria-label', 'aria-labelledby'}
valid_t_attrs = {'t-value', 't-raw', 't-field', 't-esc', 't-out'}

def has_text(node):
    return node is not None and bool((node.text or '').strip())

def has_title_or_aria_label(node):
    return any(node.get(attr) for attr in valid_aria_attrs)

def contains_description(node, depth=0):
    if depth > 2:
        return False
    if any(node.get(attr) for attr in valid_t_attrs):
        return True
    if has_title_or_aria_label(node):
        return True
    if node.tag in ('label', 'field'):
        return True
    if node.text and node.text.strip():
        return True
    return any(contains_description(child, depth+1) for child in node)

warnings = []

for fpath in glob.glob("views/**/*.xml", recursive=True):
    try:
        tree = etree.parse(fpath)
    except Exception as e:
        continue
    for node in tree.xpath("//i[contains(@class, 'fa')]"):
        if node.tail and node.tail.strip():
            continue
        prev = node.getprevious()
        nxt = node.getnext()
        if has_text(prev) or (prev is not None and prev.tail and prev.tail.strip()):
            continue
        if has_text(nxt):
            continue
        if has_title_or_aria_label(node):
            continue
        if any(map(has_title_or_aria_label, node.iterancestors())):
            continue
        if node.get('string'):
            continue
        if contains_description(node):
            continue
        
        parent_record = node.xpath("ancestor::record[1]")
        rec_id = parent_record[0].get('id') if parent_record else 'unknown'
        warnings.append((fpath, node.sourceline, etree.tostring(node, encoding='unicode').strip(), rec_id))

print(f"Total warnings found: {len(warnings)}")
for w in warnings:
    print(f"{w[0]}:{w[1]} in record {w[3]}: {w[2]}")
