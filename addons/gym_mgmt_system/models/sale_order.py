# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Sahla Sherin (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, _


class SaleOrder(models.Model):
    """Inherit the sale.order model for supering the action confirm."""
    _inherit = "sale.order"

    def action_confirm(self):
        """ Membership  created directly from sale order confirmed """
        product = self.env['product.product'].search([
            ('membership_date_from', '!=', False),
            ('id', '=', self.order_line.product_id.id)])
        for record in product:
            self.env['gym.membership'].create([
                {'member_id': self.partner_id.id,
                 'membership_date_from': record.membership_date_from,
                 'membership_scheme_id': self.order_line.product_id.id,
                 'sale_order_id': self.id,
                 }])

        res = super(SaleOrder, self).action_confirm()
        return res
