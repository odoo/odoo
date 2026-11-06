import re

def inspect_file(filename):
    print("=== " + filename + " ===")
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    records = re.findall(r'<record id="([^"]+)" model="ir\.ui\.view">.*?<field name="arch"[^>]*>([\s\S]*?)</field>', content)
    for rec_id, arch in records:
        if '<kanban' in arch:
            print(f"Record: {rec_id}")
            match = re.search(r'<kanban([^>]*)>', arch)
            if match:
                print(f"  kanban attrs: {match.group(1).strip()}")
            templates = re.findall(r'<t t-name="([^"]+)"', arch)
            print(f"  templates: {templates}")

for fn in ['views/assignment_views.xml', 'views/attendance_views.xml', 'views/class_section_views.xml', 'views/menu_views.xml']:
    inspect_file(fn)
