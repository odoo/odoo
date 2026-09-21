from odoo import fields, models


class AccountConfig(models.Model):
    _inherit = "account.config"

    vat_check_vies = fields.Boolean(string="Verify VAT Numbers")
