# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Chethana Ramachandran(<https://www.cybrosys.com>)
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
from odoo import fields, models


class Pricelist(models.Model):
    """Inherits the Product Pricelist to update the _compute_price_rule
     function for adding the product uom in price rule."""
    _inherit = "product.pricelist"

    def _compute_price_rule(self, products, qty, uom=None, date=False,
                            **kwargs):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given
        price list}
        :param products: recordset of products
        (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions
        :type date: date or datetime
        :returns: product_id: (price, pricelist_rule)
        :rtype: dict
        """
        self.ensure_one()
        if not products:
            return {}
        if not date:
            date = fields.Datetime.now()
        rules = self._get_applicable_rules(products, date, **kwargs)
        results = {}
        for product in products:
            suitable_rule = self.env['product.pricelist.item']
            target_uom = uom or product.uom_id
            for rule in rules:
                if rule._is_applicable_for(product, qty, uom):
                    suitable_rule = rule
                    break
            kwargs['pricelist'] = self
            price = suitable_rule._compute_price(product, qty, target_uom,
                                                 date=date,
                                                 currency=self.currency_id)
            results[product.id] = (price, suitable_rule.id)
        return results
