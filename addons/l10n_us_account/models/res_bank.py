from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResBank(models.Model):
    _inherit = "res.bank"

    intermediary_bank_id = fields.Many2one(
        comodel_name="res.bank",
        help="An intermediary bank facilitates international wire transfers between your bank and the beneficiary's bank when they don’t have a direct relationship.",
        domain="[('id', '!=', id)]",
    )

    @api.constrains("intermediary_bank_id")
    def _constrains_intermediary_bank_id(self):
        for bank in self:
            if bank == bank.intermediary_bank_id:
                raise ValidationError(_("A bank cannot be its own intermediary bank."))
