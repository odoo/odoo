# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_pk_is_further_tax = fields.Boolean(
        string="Is Further Tax",
        help="This field is used in the Pakistan e-invoicing or e-receipt integration",
    )
