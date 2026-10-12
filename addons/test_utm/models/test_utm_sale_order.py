# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TestUtmSaleOrder(models.Model):
    _name = 'test.utm.sale.order'
    _inherit = ['utm.mixin']
    _description = 'Fake Sale Order to test UTMs'

    amount = fields.Integer('Amount')
