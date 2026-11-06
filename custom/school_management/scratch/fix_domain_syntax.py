model_file = "custom/school_management/models/timetable.py"
with open(model_file, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("from odoo.osv import expression\n", "")
text = text.replace("expression.AND([search_domain, domain])", "Domain.AND([search_domain, domain])")

with open(model_file, "w", encoding="utf-8") as f:
    f.write(text)
print("Updated domain syntax in timetable.py")
