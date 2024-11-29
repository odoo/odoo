from . import models
from . import wizard


def _l10n_in_tds_post_init(env):
    for company in env['res.company'].search([('chart_template', '=', 'in'), ('parent_id', '=', False)]):
        env['res.company']._l10n_in_load_tds_chart_of_accounts_and_taxes(company)
        tds_group_id = env.ref(f'account.{company.id}_tds_group', raise_if_not_found=False)
        if tds_group_id:
            tds_purchase_taxes = env['account.tax'].with_context(active_test=False).search([('tax_group_id', '=', tds_group_id.id), ('type_tax_use', '=', 'purchase')])
            tds_purchase_taxes.write({'l10n_in_tds_tax_type': 'purchase', 'type_tax_use': 'none'})
