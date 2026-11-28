path = r"c:\Odoo\odoo\custom\school_management\views\dashboard_views.xml"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace('<i class="fa fa-arrow-right ms-1" aria-hidden="true"></i>', '<i class="fa fa-arrow-right ms-1" aria-hidden="true" title="View"></i>')

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Updated dashboard_views.xml")
