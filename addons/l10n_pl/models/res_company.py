from odoo import fields, models
from odoo.addons import account, base_vat


class ResCompany(base_vat.ResCompany, account.ResCompany):

    l10n_pl_reports_tax_office_id = fields.Many2one('l10n_pl.l10n_pl_tax_office', string='Tax Office', groups="account.group_account_user")
