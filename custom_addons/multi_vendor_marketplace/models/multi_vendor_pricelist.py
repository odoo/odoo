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
from odoo import api, fields, models


class MultiVendorPriceList(models.Model):
    """Create a new class MultiVendorPriceList for vendor price-list."""
    _name = 'multi.vendor.pricelist'
    _description = "Multi vendor pricelist"

    price_list_id = fields.Many2one('product.pricelist',
                                    string='Price list', help='Price list')
    price_of_pricelist = fields.Float(required=True, String='Price',
                                      help='Price')
    min_qty = fields.Integer(required=True, string='Minimum quantity',
                             help='Minimum quantity')
    start_date = fields.Date(required=True, string='Start Date',
                             help='Start Date')
    end_date = fields.Date(required=True, string='Start Date',
                           help='Start Date')
    product_inv_id = fields.Many2one('product.template',
                                     string='Product', help='Product',
                                     ondelete='cascade')

    @api.ondelete(at_uninstall=False)
    def delete_pricelist(self):
        """ PRICE-LIST LINE DELETE FROM PRODUCT FORM VIEW AND
        PRICE-LIST-VIEW """
        query = """delete from product_pricelist_item where 
        pricelist_multivendor_id = %s """ % self.id
        self.env.cr.execute(query)
