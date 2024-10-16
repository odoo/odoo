from odoo import models, fields
from odoo.addons import account


class ResCompany(account.ResCompany):

    l10n_ca_pst = fields.Char(related='partner_id.l10n_ca_pst', string='PST Number', store=False, readonly=False)


class BaseDocumentLayout(account.BaseDocumentLayout):

    l10n_ca_pst = fields.Char(related='company_id.l10n_ca_pst', readonly=True)
    account_fiscal_country_id = fields.Many2one(related="company_id.account_fiscal_country_id", readonly=True)
