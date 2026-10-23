from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    account_ledger_ids = fields.One2many(comodel_name="account.move.line", inverse_name="partner_id")

