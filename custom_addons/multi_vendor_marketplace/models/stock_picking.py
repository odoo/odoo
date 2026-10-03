# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from odoo import fields, models


class StockPicking(models.Model):
    """Picking added with seller's extra details for the products the sell"""
    _inherit = 'stock.picking'

    seller_id = fields.Many2one('res.partner', string="Seller",
                                help="Seller information")
    ref_id = fields.Integer(string="Refer id", help="For adding the reference")

    def button_validate(self):
        """ Super stock picking function for fetch deliverd qty from delivery
            form to sale order """
        res = super(StockPicking, self).button_validate()
        sale_order_line_rec = self.env['sale.order.line'].sudo().search(
            [('id', '=', self.ref_id)])
        sale_order_line_rec.state = 'shipped'
        sale_order_line_rec.update({
            'qty_delivered': self.move_ids_without_package.quantity_done
        })
        return res
