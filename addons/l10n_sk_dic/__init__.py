# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models


def _l10n_sk_dic_post_init(env):
    """Move the income tax ID of the existing companies to their contact.

    The old column is read directly, as income_tax_id is now related to the
    partner field.
    """
    env.cr.execute("SELECT id, income_tax_id FROM res_company WHERE income_tax_id IS NOT NULL")
    for company_id, dic in env.cr.fetchall():
        env['res.company'].browse(company_id).partner_id.l10n_sk_dic = dic
