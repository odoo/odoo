path = r"c:\Odoo\odoo\custom\school_management\views\portal_templates.xml"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace any <i class="fa ... aria-hidden="true"/> with title attribute
import re
def repl(match):
    s = match.group(0)
    if 'title=' in s or 'aria-label=' in s:
        return s
    # Add title based on icon name
    m_icon = re.search(r'fa-([a-zA-Z0-9-]+)', s)
    title_val = m_icon.group(1).replace('-', ' ').capitalize() if m_icon else 'Icon'
    return s[:-2] + f' title="{title_val}" aria-label="{title_val}"/>'

c_new = re.sub(r'<i\s+class="fa\s+[^"]*"\s*aria-hidden="true"\s*/>', repl, c)
if c_new != c:
    with open(path, "w", encoding="utf-8") as f:
        f.write(c_new)
    print("Updated portal_templates.xml")
else:
    print("No changes in portal_templates.xml")
