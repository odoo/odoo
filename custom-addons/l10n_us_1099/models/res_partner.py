# coding: utf-8
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    box_1099_id = fields.Many2one(
        "l10n_us.1099_box",
        string="1099 Box",
        help="Journal items of this vendor will be summed in the selected box of the 1099 report."
    )
