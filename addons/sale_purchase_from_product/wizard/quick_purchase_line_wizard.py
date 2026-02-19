# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import fields, models, api


class QuickPurchaseOrderLines(models.TransientModel):
    _name = 'quick.purchase.line.wizard'
    _description = 'Quick Purchase Line Wizard'

    order_id = fields.Many2one('quick.purchase.wizard')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string="Quantity")
    price_unit = fields.Float(string="Unit Price", required=True)
    tax_id = fields.Many2many(comodel_name='account.tax', string="Taxes")

