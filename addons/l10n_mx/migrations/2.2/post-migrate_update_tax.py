# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, SUPERUSER_ID
from odoo.addons.account.models.chart_template import update_taxes_from_templates


def migrate(cr, version):
    # Create new accounts for each MX company if accounts with relevant codes aren't already present
    # Create DIOT 2025 taxes dependent on these accounts
    env = api.Environment(cr, SUPERUSER_ID, {})
    new_account_vals_list = [
        {
            'template_xmlid': 'cuenta118_01_02',
            'values': {
                'name': "IVA acreditable pagado al 8%",
                'code': '118.01.02',
                'account_type': 'asset_current',
                'reconcile': False,
                'tag_ids': [env.ref('l10n_mx.tag_debit_balance_account').id],
            },
        },
        {
            'template_xmlid': 'cuenta118_02',
            'values': {
                'name': "IVA acreditable de importación pagado",
                'code': '118.02.01',
                'account_type': 'asset_current',
                'reconcile': False,
                'tag_ids': [env.ref('l10n_mx.tag_debit_balance_account').id],
            },
        },
        {
            'template_xmlid': 'cuenta119_02',
            'values': {
                'name': "IVA de importación pendiente de pago",
                'code': '119.02.01',
                'account_type': 'asset_current',
                'reconcile': True,
                'tag_ids': [env.ref('l10n_mx.tag_debit_balance_account').id],
            },
        },
        {
            'template_xmlid': 'cuenta601_58',
            'values': {
                'name': "Otros impuestos y derechos",
                'code': '601.58.01',
                'account_type': 'expense',
                'reconcile': False,
                'tag_ids': [env.ref('l10n_mx.tag_debit_balance_account').id],
            },
        }
    ]
    for company in env['res.company'].search([('chart_template_id', '=', env.ref('l10n_mx.mx_coa').id)]):
        for account in new_account_vals_list:
            new_account_vals = {'values': account['values'].copy()}
            new_account_vals['values']['company_id'] = company.id
            # Taxes are linked by code, so if an account with this code was already created by the user, nothing needs to be done
            if not env['account.account'].search([('code', '=', new_account_vals['values']['code']), ('company_id', '=', company.id)]):
                # If the template XMLid does not already exist in the database, add it to the vals
                if not env.ref(f"account.{company.id}_{account['template_xmlid']}", raise_if_not_found=False):
                    new_account_vals['xml_id'] = f"account.{company.id}_{account['template_xmlid']}"
                env['account.account']._load_records([new_account_vals])
    update_taxes_from_templates(cr, 'l10n_mx.mx_coa')
