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
from odoo import api, fields, models


class PricelistItem(models.Model):
    """Inherits the Product Price list Item Class to compute the product uom and
    want to apply in the price list"""
    _inherit = "product.pricelist.item"

    product_uom_category_id = fields.Many2one(
        string="Product UOM Category",
        related='product_tmpl_id.uom_id.category_id',
        depends=['product_tmpl_id'],
        help="Defines the product uom category of the product")
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string="Unit of Measure",
        compute='_compute_product_uom_id',
        store=True, readonly=False, precompute=True, ondelete='restrict',
        domain="[('category_id', '=', product_uom_category_id)]",
        help="Defines the product uom of the product")

    @api.depends('product_tmpl_id')
    def _compute_product_uom_id(self):
        """Computes the product uom, and it depends on the product template"""
        for line in self:
            if not line.product_uom_id or (
                    line.product_tmpl_id.uom_id.id != line.product_uom_id.id):
                line.product_uom_id = line.product_tmpl_id.uom_id
            else:
                line.product_uom_id = False

    def _is_applicable_for(self, product, qty, uom_id):
        """Check whether the current rule is valid for the given product & qty.
        Note: self.ensure_one()
        :param product: product record (product.product/product.template)
        :param float qty_in_product_uom: quantity, expressed in product UoM
        :returns: Whether rules is valid or not
        :rtype: bool
        """
        self.ensure_one()
        product.ensure_one()
        res = True
        is_product_template = product._name == 'product.template'
        if self.min_quantity and qty < self.min_quantity:
            res = False
        elif self.product_uom_id and uom_id.id != self.product_uom_id.id:
            res = False
        elif self.categ_id:
            cat = product.categ_id
            while cat:
                if cat.id == self.categ_id.id:
                    break
                cat = cat.parent_id
            if not cat:
                res = False
        else:
            if is_product_template:
                if self.product_tmpl_id and product.id != self.product_tmpl_id.id:
                    res = False
                elif self.product_id and not (
                        product.product_variant_count == 1 and
                        product.product_variant_id.id == self.product_id.id):
                    res = False
            else:
                if self.product_tmpl_id and product.product_tmpl_id.id != self.product_tmpl_id.id:
                    res = False
                elif self.product_id and product.id != self.product_id.id:
                    res = False
        return res
