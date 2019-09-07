# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons.base.models.res_partner import WARNING_MESSAGE, WARNING_HELP


class Partner(models.Model):
    _inherit = 'res.partner'

    property_stock_customer = fields.Many2one(
        'stock.location', string="Customer Location", company_dependent=True,
        help="The stock location used as destination when sending goods to this contact.")
    property_stock_supplier = fields.Many2one(
        'stock.location', string="Vendor Location", company_dependent=True,
        help="The stock location used as source when receiving goods from this contact.")
    picking_warn = fields.Selection(WARNING_MESSAGE, 'Stock Picking', help=WARNING_HELP, default='no-message')
    # TDE FIXME: expand this message / help
    picking_warn_msg = fields.Text('Message for Stock Picking')
