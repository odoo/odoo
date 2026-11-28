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
    payment = env["university.payment"].browse(1216)
    print("Payment found:", payment.name)
    report_action = env.ref("school_management.action_report_university_payment_receipt")
    pdf_content, ext = report_action._render_qweb_pdf("school_management.action_report_university_payment_receipt", res_ids=payment.ids)
    print(f"PDF generated successfully! Size: {len(pdf_content)} bytes, ext: {ext}")
