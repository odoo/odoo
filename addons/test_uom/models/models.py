# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TestUomLine(models.Model):
    _name = 'test_uom.line'
    _description = 'Test Uom Line'

    product_id = fields.Many2one('product.product', required=True)
    uom_id = fields.Many2one('uom.uom', required=True)
    qty = fields.Measure()
