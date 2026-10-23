# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Dhanya Babu (odoo@cybrosys.com)
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
################################################################################
from odoo import fields, models


class ProductTemplate(models.Model):
    """ we need ot inherit this model for displaying the
     particular pricelist on each product template"""
    _inherit = 'product.template'

    product_pricelist_ids = fields.Many2many('pricelist.product',
                                             string='Product Pricelists',
                                             help='Displaying the pricelist',
                                             readonly=True)
    has_pricelist = fields.Boolean(string='Has Pricelist',
                                   help='Specify whether the product has '
                                        'different prices',
                                   compute='_compute_has_pricelist')

    def _compute_has_pricelist(self):
        """Method _compute_has_pricelist to compute the value to the field
        has_pricelist"""
        for rec in self:
            rec.has_pricelist = True if rec.product_pricelist_ids else False
