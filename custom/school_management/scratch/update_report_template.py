path = r"c:\Odoo\odoo\custom\school_management\reports\payment_report_template.xml"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("o.student_id.company_id.name or res_company.name", "res_company.name")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Updated payment_report_template.xml")
