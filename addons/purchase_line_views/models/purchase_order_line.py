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


from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    """ For adding product image directly
    to purchase order line from product"""

    _inherit = 'purchase.order.line'

    product_image = fields.Binary(
        related="product_id.image_1920",
        help='For getting product image '
             'to purchase order line')

    @api.onchange('order_id')
    def onchange_order_id(self):
        """ Restrict creating purchase order line for purchase order
                in locked,cancel and purchase order states"""
        
        if self.order_id.state in ['cancel', 'done', 'purchase']:
            raise UserError(_("You cannot select purchase order in "
                              "cancel or locked or purchase order state"))
