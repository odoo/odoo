# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError



class LicensePlateOrders(models.Model):
    _name = 'license.plate.orders'
    _description = 'License Plate Model'

    name = fields.Char(string='License Plate Name')
    license_plate_order_line_ids = fields.One2many('license.plate.orders.line', 'license_plate_orders_id',
                               string='License Plate Lines')
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='State', default='open')
    automation_manual = fields.Selection([('automation', 'Automation'),
                                          ('manual', 'Manual')], string='Automation Manual')


    def action_open(self):
        for rec in self:
            rec.state = 'open'



class LicensePlateOrdersLine(models.Model):
    _name = 'license.plate.orders.line'
    _description = 'License Plate Orders Line'
    _order = 'sequence, id'

    name = fields.Char(string='Name')
    license_plate_orders_id = fields.Many2one(
        comodel_name='license.plate.orders',
        string='License Plate Orders',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string="Sequence")
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
    )
    quantity = fields.Float(string='Quantity', required=True)
    sku_code = fields.Char(string='SKU')
    barcode = fields.Char(string='Barcode')
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='State', default='open')

    def button_close_license_plate(self):
        """
        Close the license plate for this delivery receipt order line.
        This method sets the license_plate_closed field to True
        and updates the state to 'closed'.
        """
        self.license_plate_closed = True
        self.state = 'closed'

