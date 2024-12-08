# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_delivery_carrier_id = fields.Many2one('delivery.carrier', company_dependent=True, string="Delivery Method", help="Used in sales orders.")
    is_pickup_location = fields.Boolean()  # Whether it is a pickup point address.

    def _get_delivery_address_domain(self):
        return expression.AND([
            super()._get_delivery_address_domain(),
            [('is_pickup_location', '=', False)],
        ])
