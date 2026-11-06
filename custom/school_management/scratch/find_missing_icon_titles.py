import re
import glob

# Odoo rule in ir_ui_view:
# Every <i> with class containing 'fa' must have title attribute or text content, or its parent must have title/text.
for fpath in glob.glob("views/**/*.xml", recursive=True):
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # find all <i ...> or <i .../>
    for m in re.finditer(r'<i\b([^>]*)>(.*?)</i>|<i\b([^>]*)/?>', content, re.DOTALL):
        tag_attrs = m.group(1) or m.group(3) or ""
        inner_text = (m.group(2) or "").strip()
        if "fa-" in tag_attrs or "fa " in tag_attrs:
            if "title=" not in tag_attrs and "aria-label=" not in tag_attrs and not inner_text:
                # Find line number
                line_no = content[:m.start()].count("\n") + 1
                matched_str = m.group(0).replace("\n", " ").strip()
                print(f"{fpath}:{line_no} -> {matched_str}")
