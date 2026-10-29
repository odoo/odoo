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
from odoo import api, fields, models


class ProductTemplate(models.Model):
    """This class represents margin on products"""
    _inherit = 'product.template'

    margin_percent_product = fields.Float(string='Margin %',
                                          compute='compute_margin', store=True,
                                          help='Field to store the margin in'
                                               ' percentage of the product')

    @api.depends('list_price', 'standard_price')
    def compute_margin(self):
        """Method to compute the margin of the product."""
        self.margin_percent_product = 0
        for record in self:
            if record.list_price and record.standard_price:
                record.margin_percent_product = ( record.list_price - record.standard_price) / record.list_price
