# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Dhanya Babu (<https://www.cybrosys.com>)
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
from odoo import api, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    """Inheriting  sale order model to check the order line count  when
        confirm the sale order."""
    _inherit = 'sale.order'

    @api.constrains('order_line')
    def _check_order_line(self):
        """This function ensures that the same product cannot be added with
           the same location more than once in the order."""
        for order in self:
            for line in order.order_line.filtered(
                    lambda l: l.line_location_id):
                lines_count = line.search_count([('order_id', '=', order.id), (
                    'product_id', '=', line.product_id.id),
                                                 ('line_location_id', '=',
                                                  line.line_location_id.id)])
                if lines_count > 1:
                    raise ValidationError(
                        _(f"You cannot add the same product"
                          f" {line.product_id.display_name} with the same "
                          f"location '{line.line_location_id.name}'."))
