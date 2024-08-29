from odoo import models, fields
from odoo.addons import account


class AccountAccount(models.Model, account.AccountAccount):

    l10n_pt_taxonomy_code = fields.Integer(string="Taxonomy code")
