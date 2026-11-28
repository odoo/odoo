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
    
    # Find sample fee invoice with lines and payments
    fee = env['university.fee'].search([('line_ids', '!=', False), ('paid_amount', '>', 0)], limit=1)
    if not fee:
        fee = env['university.fee'].search([('line_ids', '!=', False)], limit=1)
    print(f"Testing with Fee ID: {fee.id}, Name: {fee.name}")

    # Also find a draft fee and an overdue fee
    draft_fee = env['university.fee'].search([('state', '=', 'draft')], limit=1)
    overdue_fee = env['university.fee'].search([('payment_state', '=', 'overdue')], limit=1)
    print(f"Draft Fee: {draft_fee.id if draft_fee else None}, Overdue Fee: {overdue_fee.id if overdue_fee else None}")
