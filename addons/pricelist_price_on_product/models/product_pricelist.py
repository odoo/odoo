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
from odoo import api, fields, models


class ProductPricelist(models.Model):
    """Need of this model is because we need to add boolean field  to
     display the pricelist in the product form by checking ,
     whether the boolean true or false"""
    _inherit = 'product.pricelist'

    display_pricelist = fields.Boolean(string='Display Pricelist Price on '
                                              'Products',
                                       help='If we want to display the '
                                            'pricelist on product form ,we can '
                                            'enable this boolean field')

    @api.onchange('display_pricelist', 'item_ids')
    def _onchange_display_pricelist(self):
        """displaying pricelist on product"""
        for item in self:
            pricelist_ids = item.item_ids.mapped(
                'product_tmpl_id.product_pricelist_ids')
            for line in item.item_ids:
                product = line.product_tmpl_id
                existing_pricelist = pricelist_ids.filtered(
                    lambda p: p.product_price_id.id == item.ids[0])
                if item.display_pricelist:
                    if not existing_pricelist:
                        product.write({
                            'product_pricelist_ids': [
                                (0, 0, {
                                    'product_price_id': item.ids[0],
                                    'product_price': line.fixed_price,
                                })
                            ],
                        })
                    else:
                        existing_pricelist.write(
                            {'product_price': line.fixed_price})
                elif existing_pricelist:
                    existing_pricelist.unlink()
