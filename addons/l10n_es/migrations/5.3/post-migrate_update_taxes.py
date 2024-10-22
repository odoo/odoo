# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID
from odoo.addons.account.models.chart_template import update_taxes_from_templates


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env.companies:
        taxes_to_disable = (
            f'{company.id}_account_tax_template_p_iva5_ic_bc',
            f'{company.id}_account_tax_template_p_iva5_ic_sc',
            f'{company.id}_account_tax_template_p_iva5_ibc',
            f'{company.id}_account_tax_template_p_iva5_isc',
            f'{company.id}_account_tax_template_p_iva5_bc',
            f'{company.id}_account_tax_template_p_iva5_sc',
            f'{company.id}_account_tax_template_p_iva5_nd',
            f'{company.id}_account_tax_template_s_iva5s',
            f'{company.id}_account_tax_template_s_iva5b',
            f'{company.id}_account_tax_template_s_req062',
            f'{company.id}_account_tax_template_p_req062',
        )
        tax_ids = env['ir.model.data'].search([
            ('name', 'in', taxes_to_disable),
            ('model', '=', 'account.tax'),
        ]).mapped('res_id')
        env['account.tax'].browse(tax_ids).active = False

    update_taxes_from_templates(cr, 'l10n_es.account_chart_template_common')
