from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['account.report.expression'].search([
        ('label', '=', 'balance'),
        ('report_line_id.code', 'in', [f'VL{n}' for n in (3, 4, 32, 33)]),
        ('report_line_id.report_id.name', '=', 'VL VAT Report'),
    ]).unlink()
