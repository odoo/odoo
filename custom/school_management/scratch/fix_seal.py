path = r"c:\Odoo\odoo\custom\school_management\reports\payment_report_template.xml"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

target = """<div style="width: 80px; height: 80px; border: 1.5px dashed #a51c30; border-radius: 50%; margin: 0 auto; display: flex; align-items: center; justify-content: center; text-align: center; font-size: 9px; font-weight: bold; color: #7c1728; line-height: 1.2; padding-top: 24px;">"""

replacement = """<div style="box-sizing: border-box; width: 80px; height: 80px; border: 1.5px dashed #a51c30; border-radius: 50%; margin: 0 auto; text-align: center; font-size: 9px; font-weight: bold; color: #7c1728; line-height: 1.2; padding-top: 24px;">"""

c = c.replace(target, replacement)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Updated seal styling in payment_report_template.xml")
