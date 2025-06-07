# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class Product(models.Model):
    _inherit = "product.product"

    product_catalog_product_is_in_repair = fields.Boolean(
        compute='_compute_product_is_in_repair',
        search='_search_product_is_in_repair',
    )

    def _compute_product_is_in_repair(self):
        # Just to enable the _search method
        self.product_catalog_product_is_in_repair = False

    def _search_product_is_in_repair(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_("Operation not supported"))
        product_ids = self.env['repair.order'].search([
            ('id', 'in', [self.env.context.get('order_id', '')]),
        ]).move_ids.product_id.ids
        if (operator == '!=' and value is True) or (operator == '=' and value is False):
            domain_operator = 'not in'
        else:
            domain_operator = 'in'
        return [('id', domain_operator, product_ids)]

    def _count_returned_sn_products_domain(self, sn_lot, or_domains):
        or_domains.append([
                ('move_id.repair_line_type', 'in', ['remove', 'recycle']),
                ('location_dest_usage', '=', 'internal'),
        ])
        return super()._count_returned_sn_products_domain(sn_lot, or_domains)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    create_repair = fields.Boolean('Create Repair', help="Create a linked Repair Order on Sale Order confirmation of this product.", groups='stock.group_stock_user')

    def copy_data(self, default=None):
        default = dict(default or {})
        if not (self.env.user.has_group('stock.group_stock_user') or self.env.is_superuser()):
            default = dict(default or {}, create_repair=False)
        return super().copy_data(default)
