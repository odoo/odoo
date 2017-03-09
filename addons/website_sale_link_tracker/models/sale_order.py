# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ['utm.mixin', 'sale.order']
