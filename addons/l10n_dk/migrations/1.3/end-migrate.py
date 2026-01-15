from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'dk')], order="parent_path"):
        tax = env.ref(f'account.{company.id}_tax_keumf', raise_if_not_found=False)
        if tax:
            tax.type_tax_use = 'purchase'
