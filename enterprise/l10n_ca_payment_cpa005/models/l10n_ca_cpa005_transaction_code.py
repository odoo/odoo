# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class L10nCACPA005TransactionCode(models.Model):
    _name = "l10n_ca_cpa005.transaction.code"
    _description = "Canadian EFT transaction codes as defined in Payments Canada Standard 007"
    _rec_names_search = ["name", "code"]

    name = fields.Char("Name", required=True)
    active = fields.Boolean("Active", default=True)
    code = fields.Char("Code", required=True)

    @api.depends("name", "code")
    def _compute_display_name(self):
        for tx_code in self:
            tx_code.display_name = f"[{tx_code.code}] {tx_code.name}"
