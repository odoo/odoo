# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'ch')], order="parent_path"):
        # We had corrupted data, handle the correction so the tax update can proceed.
        # See https://github.com/odoo/odoo/commit/7b07df873535446f97abc1de9176b9332de5cb07
        taxes_to_check = (f'{company.id}_vat_purchase_81_reverse', f'{company.id}_vat_77_purchase_reverse')
        tax_ids = env['ir.model.data'].search([
            ('name', 'in', taxes_to_check),
            ('model', '=', 'account.tax'),
        ]).mapped('res_id')
        for tax in env['account.tax'].browse(tax_ids).with_context(active_test=False):
            for child in tax.children_tax_ids:
                if child.type_tax_use not in ('none', tax.type_tax_use):
                    # set the child to it's parent's value
                    child.type_tax_use = tax.type_tax_use

        env['account.chart.template'].try_loading('ch', company)
