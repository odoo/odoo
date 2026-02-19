# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Saneen K (odoo@cybrosys.com)
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
###############################################################################
from odoo import fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    """Inherit the Sale Order for make the field editable to security group"""
    _inherit = 'sale.order'

    def readonly_field(self):
        """Function that for making the field readonly"""
        return {
            state: [('readonly', False)] for state in {
                'sale', 'done', 'cancel'}
        }
    date_order = fields.Datetime(string="Order Date",states=readonly_field,
                                 copy=False, required=True,
                                 help="Creation date of draft/sent orders,"
                                      "\nConfirmation date of confirmed orders.")

    def write(self, values):
        """Supering the write function for making the order_date field
         readonly for particular user group"""
        result = super().write(values)
        if 'date_order' in values and values['date_order'] != self.date_order \
                and not self.env.user.has_group(
                        'edit_order_date.edit_order_date_group_user'):
            raise UserError(
                _("You have no access to change 'Order Date'"))
        return result
