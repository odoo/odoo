# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    property_delivery_carrier_id = fields.Many2one(
        string="Delivery Method",
        help="Used in sales orders.",
        comodel_name="delivery.carrier",
        company_dependent=True,
        default=lambda self: (self.env.ref("delivery.free_delivery_carrier", raise_if_not_found=False)),
    )
