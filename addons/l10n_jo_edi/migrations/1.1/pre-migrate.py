from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'jo_standard')]):
        sent_invoices_count = env['account.move'].search_count([('company_id', '=', company.id), ('l10n_jo_edi_state', '=', 'sent')])
        env['ir.config_parameter'].set_param(company._get_jo_icv_param_name(), sent_invoices_count)
