# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_delivery_carrier = fields.Many2one('delivery.carrier', string="Delivery Method", company_dependent=True, help="This delivery method will be used when invoicing from picking.")
