from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = "account.account"

    l10n_pt_taxonomy_code = fields.Integer(string="Taxonomy code")


class AccountAccountTemplate(models.Model):
    _inherit = "account.account.template"

    l10n_pt_taxonomy_code = fields.Integer(string="Taxonomy code")
