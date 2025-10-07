# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Cybrosys Technologies (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL v3) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
from odoo import fields, models


class PurchaseOrder(models.Model):
    """
        Inherit the Purchase Order model to add amount in words in purchase order.

        Methods:
            _compute_number_to_words(self):
                Function to Change the purchase order total amount to words.
    """
    _inherit = 'purchase.order'

    number_to_words = fields.Char(string="Amount in Words (Total) : ",
                                  compute='_compute_number_to_words',
                                  help="To showing total amount in words")

    def _compute_number_to_words(self):
        """Compute the amount to words in Purchase Order"""
        for rec in self:
            rec.number_to_words = rec.currency_id.amount_to_text(
                rec.amount_total)
