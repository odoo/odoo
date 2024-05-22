# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Product(models.Model):
    _inherit = "product.product"

    product_catalog_product_is_in_repair = fields.Boolean(
        compute='_compute_product_is_in_repair',
        search='_search_product_is_in_repair',
    )

    @api.depends_context('order_id')
    def _compute_product_is_in_repair(self):
        repair_id = self.env.context.get('order_id')
        if not repair_id:
            self.product_catalog_product_is_in_repair = False
            return

        read_group_data = self.env['stock.move']._read_group(
            domain=[('order_id', '=', repair_id)],
            groupby=['product_id'],
            aggregates=['__count'],
        )
        data = {product.id: count for product, count in read_group_data}
        for product in self:
            product.product_catalog_product_is_in_repair = bool(data.get(product.id, 0))

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
