# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    tracking = fields.Selection([('serial', 'By Unique Serial Number'),('lot', 'By Lots'),('none', 'No Tracking')], string="Tracking", help="Ensure the traceability of a storable product in your warehouse.", default='lot', required=True)
    use_expiration_date = fields.Boolean(string='Expiration Date',help='When this box is ticked, you have the possibility to specify dates to manage'' product expiration, on the product and on the corresponding lot/serial numbers',  default='True')


class ProductProduct(models.Model):
    _inherit = "product.product"

    tracking = fields.Selection([('serial', 'By Unique Serial Number'),('lot', 'By Lots'),('none', 'No Tracking')], string="Tracking",help="Ensure the traceability of a storable product in your warehouse.", default='lot', required=True)
    use_expiration_date = fields.Boolean(string='Expiration Date',help='When this box is ticked, you have the possibility to specify dates to manage'' product expiration, on the product and on the corresponding lot/serial numbers',default='True')
