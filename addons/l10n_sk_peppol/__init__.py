from odoo.tools.sql import column_exists, create_column

from . import models
from . import wizard


def _l10n_sk_peppol_pre_init_hook(env):
    if not column_exists(env.cr, "res_partner", "l10n_sk_dic"):
        create_column(env.cr, "res_partner", "l10n_sk_dic", "varchar")


def _l10n_sk_peppol_post_init_hook(env):
    env.cr.execute("""
        UPDATE res_partner partner
           SET l10n_sk_dic = COALESCE(company.income_tax_id, SUBSTRING(partner.vat FROM 3))
          FROM res_company company
         WHERE company.partner_id = partner.id
           AND (company.income_tax_id IS NOT NULL OR partner.vat ILIKE 'SK%')
           AND partner.l10n_sk_dic IS NULL;
    """)
