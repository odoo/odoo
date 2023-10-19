# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Product(models.Model):
    _inherit = "product.product"

    def _count_returned_sn_products_domain(self, sn_lot, or_domains):
        or_domains.append([
                ('move_id.repair_line_type', 'in', ['remove', 'recycle']),
                ('location_dest_usage', '=', 'internal'),
        ])
        return super()._count_returned_sn_products_domain(sn_lot, or_domains)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    create_repair = fields.Boolean('Create Repair', help="Create a linked Repair Order on Sale Order confirmation of this product.", groups='stock.group_stock_user')
