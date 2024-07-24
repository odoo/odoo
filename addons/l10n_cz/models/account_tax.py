# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_cz_reverse_charge = fields.Boolean(
        string="Reverse Charge Tax",
        help="Indicates if the tax is to be used with reverse charge transactions",
    )
