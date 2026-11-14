path = r"C:\Odoo\odoo\custom\school_management\scripts\seed_academic_and_dashboard_data.py"
with open(path, "r", encoding="utf-8") as f:
    s = f.read()

s = s.replace("'priority': 'high',", "")
s = s.replace("'priority': 'medium',", "")

with open(path, "w", encoding="utf-8") as f:
    f.write(s)

print("FIXED")
