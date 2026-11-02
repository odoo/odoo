from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ge_wht_category_ids = fields.Many2many(related="commercial_partner_id.l10n_ge_wht_category_ids")
