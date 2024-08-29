# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base

from odoo import fields, models


class ResPartner(models.Model, base.ResPartner):

    property_delivery_carrier_id = fields.Many2one('delivery.carrier', company_dependent=True, string="Delivery Method", help="Default delivery method used in sales orders.")
