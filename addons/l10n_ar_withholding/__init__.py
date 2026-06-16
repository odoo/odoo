# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizards
from . import demo


def _post_init_hook(env):
    """ Backfill `res.company.withholding_tax_base_account_id` on AR companies that already
    had their chart loaded before this module was installed.
    """
    ar_companies = env['res.company'].sudo().search([
        ('chart_template', 'in', ('ar_base', 'ar_ri', 'ar_ex')),
        ('withholding_tax_base_account_id', '=', False),
    ])
    for company in ar_companies:
        account = env.ref(f'account.{company.id}_base_tax_account', raise_if_not_found=False)
        if account:
            company.with_company(company).withholding_tax_base_account_id = account
