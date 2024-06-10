# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations
from typing import TYPE_CHECKING

from odoo import api, fields, models
from odoo.addons import base as base
from odoo.addons import product, uom

if TYPE_CHECKING:
    from .sale_order_template import SaleOrderTemplate
else:
    SaleOrderTemplate = 'sale.order.template'


class SaleOrderTemplateOption(models.Model):
    _name = "sale.order.template.option"
    _description = "Quotation Template Option"
    _check_company_auto = True

    sale_order_template_id = fields.Many2one[SaleOrderTemplate](
        string="Quotation Template Reference",
        index=True, required=True,
        ondelete='cascade')

    company_id = fields.Many2one[base.models.Company](
        related='sale_order_template_id.company_id', store=True, index=True)

    product_id = fields.Many2one(
        comodel_name=product.models.ProductProduct,
        required=True, check_company=True,
        domain=lambda self: self._product_id_domain())

    name = fields.Text(
        string="Description",
        compute='_compute_name',
        store=True, readonly=False, precompute=True,
        required=True, translate=True)

    uom_id = fields.Many2one(
        comodel_name=uom.models.UoM,
        string="Unit of Measure",
        compute='_compute_uom_id',
        store=True, readonly=False,
        required=True, precompute=True,
        domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one[uom.models.UoMCategory](related='product_id.uom_id.category_id')
    quantity = fields.Float(
        string="Quantity",
        required=True,
        digits='Product Unit of Measure',
        default=1)

    #=== COMPUTE METHODS ===#

    @api.depends('product_id')
    def _compute_name(self):
        for option in self:
            if not option.product_id:
                continue
            option.name = option.product_id.get_product_multiline_description_sale()

    @api.depends('product_id')
    def _compute_uom_id(self):
        for option in self:
            option.uom_id = option.product_id.uom_id

    #=== BUSINESS METHODS ===#

    @api.model
    def _product_id_domain(self):
        """Returns the domain of the products that can be added as a template option."""
        return [('sale_ok', '=', True)]

    def _prepare_option_line_values(self):
        """ Give the values to create the corresponding option line.

        :return: `sale.order.option` create values
        :rtype: dict
        """
        self.ensure_one()
        return {
            'name': self.name,
            'product_id': self.product_id.id,
            'quantity': self.quantity,
            'uom_id': self.uom_id.id,
        }
