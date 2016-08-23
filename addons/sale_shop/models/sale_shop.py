# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
##########################################################################

from openerp import api, fields, models, _
from openerp.exceptions import Warning


class SaleShop(models.Model):
    _name = "sale.shop"
    _description = "Sales Shop"

    name = fields.Char(string='Shop Name', size=120, required=True)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shop_id = fields.Many2one('sale.shop', string='Shop')
