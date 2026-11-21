import sys
import subprocess
sys.path.insert(0, r"C:\Odoo\odoo")
import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

config_file = r"C:\Odoo\odoo\odoo.conf"
odoo.tools.config.parse_config(["-c", config_file])

registry = Registry("odoo")
with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    card = env["university.report.card"].browse(105)
    report = env.ref("school_management.action_report_university_report_card")
    html = report._render_qweb_html("school_management.action_report_university_report_card", [card.id])[0]
    
    with open(r"C:\Odoo\odoo\custom\school_management\scratch\test_report_card.html", "wb") as f:
        f.write(html)
    print("Saved HTML!")

# Convert to image using wkhtmltoimage
cmd = [r"C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe", r"C:\Odoo\odoo\custom\school_management\scratch\test_report_card.html", r"C:\Odoo\odoo\custom\school_management\scratch\test_report_card.png"]
res = subprocess.run(cmd, capture_output=True, text=True)
print("wkhtmltoimage exit code:", res.returncode)
print("stdout:", res.stdout)
print("stderr:", res.stderr)
