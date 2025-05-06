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
from odoo import api, models, fields


class ProductPricelistItem(models.Model):
    """For deleting price-list items"""
    _inherit = 'product.pricelist.item'

    pricelist_multivendor_id = fields.Many2one(
        'multi.vendor.pricelist',
        string='Price list Item',
        help='Price list items')

    @api.ondelete(at_uninstall=False)
    def delete_pricelist(self):
        """ PRICE-LIST LINE DELETE FROM PRODUCT FORM VIEW AND PRICE-LISTVIEW
        TRIGGER FROM PRICE-LIST VIEW """
        query = (""" delete from multi_vendor_price-list where id = %s """ %
                 self.pricelist_multivendor_id.id)
        self.env.cr.execute(query)
