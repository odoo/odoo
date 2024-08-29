from odoo import fields, models
from odoo.addons import account


class AccountTax(models.Model, account.AccountTax):

    tax_scope = fields.Selection(
        selection_add=[('merch', 'Merchandise'), ('invest', 'Investment')],
    )
