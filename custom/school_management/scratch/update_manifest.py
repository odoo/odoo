path = r"c:\Odoo\odoo\custom\school_management\__manifest__.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old_reports = """        # Reports
        "reports/payment_report_template.xml",
        "reports/payment_report.xml",
        "reports/curriculum_report_template.xml",
        "reports/curriculum_report.xml",
        "reports/attendance_reports.xml",\
"""

new_reports = """        # Reports
        "reports/academic_reports.xml",
        "reports/academic_report_templates.xml",
        "reports/payment_report_template.xml",
        "reports/payment_report.xml",
        "reports/curriculum_report_template.xml",
        "reports/curriculum_report.xml",
        "reports/attendance_reports.xml",\
"""

old_academic_reports = """        # Academic Reports
        "reports/academic_report_templates.xml",
        "reports/academic_reports.xml",\
"""

if old_reports in c and old_academic_reports in c:
    c = c.replace(old_reports, new_reports, 1)
    c = c.replace(old_academic_reports, "", 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Replaced manifest successfully")
else:
    print("Manifest patterns not found")
