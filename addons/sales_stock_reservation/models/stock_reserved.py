# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _


class StockReserved(models.Model):
    """
       This model stores details of product reservations made in sale orders.
     """
    _name = "stock.reserved"
    _description = "Reserved stock details"

    name = fields.Char(string="Name", readonly="True", help="Name")
    order_line_name = fields.Char(string="Order Line", readonly="True",
                                  help="Name of order line")
    product_id = fields.Many2one("product.product", string="Product",
                                 readonly="True", help="Product reserved")
    status = fields.Selection(
        [('reserved', 'Reserved'), ('cancelled', 'Cancelled')],
        string="Status", readonly="True", help="Status of reservation")
    reserved_quantity = fields.Float(string="Reserved Quantity",
                                     readonly="True",
                                     help="Quantity Reserved")
    sale_order_id = fields.Many2one("sale.order", string="Sale Order",
                                    readonly="True",
                                    help="Sale order")
    move_id = fields.Many2one("stock.move", string="Move Id", readonly="True",
                              help="Stock move details")

    @api.model
    def create(self, vals_list):
        """
         Create a new record for the model and generate a sequence for the name
          field if it is not provided.
          :return: the result of the parent `create()` method call
        """
        if vals_list.get('name', _('New')) == _('New'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code(
                'stock.reserved'
            ) or _('New')
        res = super().create(vals_list)
        return res
