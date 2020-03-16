# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    edicode = fields.Char(
        related="company_id.partner_id.edicode",
        string="Edicode",
        readonly=False,
        help="Edicode for eInvoice documents",
    )

    einvoice_operator_id = fields.Many2one(
        comodel_name="res.partner.operator.einvoice",
        related="company_id.partner_id.einvoice_operator_id",
        string="eInvoice Operator",
        readonly=False,
    )
