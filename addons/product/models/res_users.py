# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    has_group_sale_pricelist = fields.Boolean(
        'Sales Pricelists', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='product.group_sale_pricelist')

    has_group_pricelist_item = fields.Boolean(
        'Manage Pricelist Items', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='product.group_pricelist_item')

    has_group_product_pricelist = fields.Boolean(
        'Pricelists On Product', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='product.group_product_pricelist')

    has_group_stock_packaging = fields.Boolean(
        'Manage Product Packaging', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='product.group_stock_packaging')

    has_group_product_variant = fields.Boolean(
        'Manage Product Variants', compute='_compute_groups_id', inverse='_inverse_groups_id',
        group_xml_id='product.group_product_variant')
