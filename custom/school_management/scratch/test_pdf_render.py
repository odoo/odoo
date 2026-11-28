import sys
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
    pdf_content, ext = report._render_qweb_pdf("school_management.action_report_university_report_card", res_ids=[card.id])
    print(f"Generated PDF successfully! Size: {len(pdf_content)} bytes, ext: {ext}")
    
    with open(r"C:\Odoo\odoo\custom\school_management\scratch\test_report_card.pdf", "wb") as f:
        f.write(pdf_content)
    print("Saved to scratch/test_report_card.pdf")
