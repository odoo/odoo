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
    print("Found Card:", card.name, card.student_id.name, card.academic_year_id.name, card.semester_id.name)
    report = env.ref("school_management.action_report_university_report_card")
    html = report._render_qweb_html("school_management.action_report_university_report_card", [card.id])[0]
    print(f"Current HTML rendered successfully! Length: {len(html)}")
