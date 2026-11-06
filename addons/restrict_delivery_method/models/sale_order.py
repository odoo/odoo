# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Shafna K(odoo@cybrosys.com)
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
###############################################################################
from odoo import api, fields, models


class SaleOrder(models.Model):
    """This class contains the compute function to calculate
    the restricted delivery method"""
    _inherit = "sale.order"

    delivery_method_ids = fields.Many2many('delivery.carrier',
                                           string="Delivery Method",
                                           compute="_compute_delivery_method_ids",
                                           help="Select delivery method for "
                                                "shipping")

    @api.depends('order_line.product_template_id')
    def _compute_delivery_method_ids(self):
        """This function helps to calculate the delivery method
        for a sale order based on the field in delivery
        carrier model"""
        for rec in self:
            delivery = (self.env['delivery.carrier'].search(
                [('restrict_product_ids', 'in',
                  rec.order_line.product_template_id.ids)]))
            if delivery:
                self.delivery_method_ids = [(4, ids) for ids in delivery.ids]
            else:
                self.delivery_method_ids = False

    def _get_restrict_delivery_method(self):
        """From this function the controller gets the
        restricted methods value"""
        address = self.delivery_method_ids
        return self.env['delivery.carrier'].sudo().search(
            [('website_published', '=', True),
             ('id', 'not in', address.ids)]).available_carriers(
            address)
