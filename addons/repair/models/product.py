# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Product(models.Model):
    _inherit = "product.product"

    def _count_returned_sn_products(self, sn_lot):
        res = self.env['stock.move'].search_count([
            ('repair_line_type', '=', 'remove'),
            ('product_uom_qty', '=', 1),
            ('move_line_ids.lot_id', 'in', sn_lot.id),
            ('state', '=', 'done'),
            ('location_dest_usage', '=', 'internal'),
        ])
        return super()._count_returned_sn_products(sn_lot) + res


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _default_repair_picking_type_id(self):
        company_id = (self.company_id or self.env.company).id
        return self.env['stock.picking.type'].search([('code', '=', 'repair_operation'), ('company_id', '=?', company_id)], limit=1, order="id asc")

    create_repair = fields.Boolean('Create Repair', help="Create a linked Repair Order on Sale Order confirmation of this product.", groups='stock.group_stock_user')
    show_repair_picking_type = fields.Boolean('Show Repair Picking Type', compute="_compute_show_repair_picking_type", groups='stock.group_stock_user')
    repair_picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type', domain=lambda self: [('code', '=', 'repair_operation'), ('company_id', '=?', self.company_id.id)],
                                             help="The Operation Type in which the Repair Order is created on Create Repair action.", default=_default_repair_picking_type_id, groups='stock.group_stock_user')

    @api.depends('create_repair')
    def _compute_show_repair_picking_type(self):
        company_ids = set(self.company_id.mapped('id'))
        company_ids.add(self.env.company.id)
        ro_type_counts = self.env['stock.picking.type']._read_group(
            [
                ('code', '=', 'repair_operation'),
                ('company_id', 'in', list(company_ids)),
            ],
            groupby=['company_id'],
            aggregates=['id:count'],
        )
        ro_type_counts = {key.id: value for key, value in ro_type_counts}
        for product in self:
            company_id = (product.company_id or self.env.company).id
            product.show_repair_picking_type = product.create_repair and ro_type_counts[company_id] > 1
