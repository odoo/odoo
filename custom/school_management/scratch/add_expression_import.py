model_file = "custom/school_management/models/timetable.py"
with open(model_file, "r", encoding="utf-8") as f:
    text = f.read()

if "from odoo.osv import expression" not in text:
    text = text.replace("from odoo.fields import Domain\n", "from odoo.fields import Domain\nfrom odoo.osv import expression\n", 1)
    with open(model_file, "w", encoding="utf-8") as f:
        f.write(text)
    print("Added expression import to timetable.py")
