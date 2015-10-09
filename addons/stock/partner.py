# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_stock_customer = fields.Many2one(comodel_name='stock.location', string="Customer Location", company_dependent=True,
        help="This stock location will be used, instead of the default one, as the destination location for goods you send to this partner")
    property_stock_supplier = fields.Many2one(comodel_name='stock.location', string="Supplier Location", company_dependent=True,
        help="This stock location will be used, instead of the default one, as the source location for goods you receive from the current partner")
