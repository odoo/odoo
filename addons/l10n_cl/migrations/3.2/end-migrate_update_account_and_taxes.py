from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    if fees_payable := env.ref('l10n_cl.account_210520', raise_if_not_found=False):
        fees_payable.write({
            'account_type': 'liability_payable',
            'reconcile': True,
        })

    if remaining_tax_credit := env.ref('l10n_cl.account_110720', raise_if_not_found=False):
        remaining_tax_credit.write({
            'account_type': 'asset_receivable',
            'reconcile': True,
        })

    if remaining_tax_credit and (tg_iva_19 := env.ref('l10n_cl.tax_group_iva_19', raise_if_not_found=False)):
        tg_iva_19.tax_receivable_account_id = remaining_tax_credit
