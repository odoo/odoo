from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_gcc_dual_language_receipt = fields.Boolean(string="GCC Formatted Receipts")
