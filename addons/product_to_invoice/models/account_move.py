# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Jumana Jabin MP (<https://www.cybrosys.com>)
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
from odoo import models


class AccountMove(models.Model):
    """Inherits the account_move model to add custom functionality."""
    _inherit = 'account.move'

    def action_add_product(self):
        """Action method to open the product_product view and add products
        to the invoice."""
        self.ensure_one()
        return {
            'name': 'Product Variants',
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'kanban,list,form',
            'target': 'current',
            'context': {'add_to_invoice': True},
        }
