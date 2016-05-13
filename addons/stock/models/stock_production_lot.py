# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductionLot(models.Model):
    _name = 'stock.production.lot'
    _inherit = ['mail.thread']
    _description = 'Lot/Serial'

    name = fields.Char(
        'Lot/Serial Number', default=lambda self: self.env['ir.sequence'].next_by_code('stock.lot.serial'),
        required=True, help="Unique Lot/Serial Number")
    ref = fields.Char('Internal Reference', help="Internal reference number in case it differs from the manufacturer's lot/serial number")
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('type', 'in', ['product', 'consu'])], required=True)
    product_uom_id = fields.Many2one(
        'product.uom', 'Unit of Measure',
        related='product_id.uom_id', store=True)
    quant_ids = fields.One2many('stock.quant', 'lot_id', 'Quants', readonly=True)
    create_date = fields.Datetime('Creation Date')
    product_qty = fields.Float('Quantity', compute='_product_qty')

    _sql_constraints = [
        ('name_ref_uniq', 'unique (name, product_id)', 'The combination of serial number and product must be unique !'),
    ]

    @api.one
    @api.depends('quant_ids.qty')
    def _product_qty(self):
        self.product_qty = sum(self.quant_ids.mapped('qty'))

    @api.multi
    def action_traceability(self):
        move_ids = self.mapped('quant_ids').mapped('history_ids').ids
        if not move_ids:
            return False
        return {
            'domain': [('id', 'in', move_ids)],
            'name': _('Traceability'),
            'view_mode': 'tree,form',
            'view_type': 'form',
            'context': {'tree_view_ref': 'stock.view_move_tree'},
            'res_model': 'stock.move',
            'type': 'ir.actions.act_window'}
