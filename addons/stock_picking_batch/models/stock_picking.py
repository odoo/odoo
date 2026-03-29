# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    count_picking_batch = fields.Integer(compute='_compute_picking_count')
    count_picking_wave = fields.Integer(compute='_compute_picking_count')

    def _compute_picking_count(self):
        super()._compute_picking_count()
        domains = {
            'count_picking_batch': [('is_wave', '=', False)],
            'count_picking_wave': [('is_wave', '=', True)],
        }
        for field in domains:
            data = self.env['stock.picking.batch'].read_group(domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['picking_type_id'])
            count = {
                x['picking_type_id'][0]: x['picking_type_id_count']
                for x in data if x['picking_type_id']
            }
            for record in self:
                record[field] = count.get(record.id, 0)

    def get_action_picking_tree_batch(self):
        return self._get_action('stock_picking_batch.stock_picking_batch_action')

    def get_action_picking_tree_wave(self):
        return self._get_action('stock_picking_batch.action_picking_tree_wave')


class StockPicking(models.Model):
    _inherit = "stock.picking"

    batch_id = fields.Many2one(
        'stock.picking.batch', string='Batch Transfer',
        check_company=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help='Batch associated to this transfer', copy=False)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if vals.get('batch_id'):
            if not res.batch_id.picking_type_id:
                res.batch_id.picking_type_id = res.picking_type_id[0]
            res.batch_id._sanity_check()
        return res

    def write(self, vals):
        batches = self.batch_id
        res = super().write(vals)
        if vals.get('batch_id'):
            batches.filtered(lambda b: not b.picking_ids).state = 'cancel'
            if not self.batch_id.picking_type_id:
                self.batch_id.picking_type_id = self.picking_type_id[0]
            self.batch_id._sanity_check()
        return res

    def action_add_operations(self):
        view = self.env.ref('stock_picking_batch.view_move_line_tree_detailed_wave')
        return {
            'name': _('Add Operations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'view': view,
            'views': [(view.id, 'tree')],
            'res_model': 'stock.move.line',
            'target': 'new',
            'domain': [
                ('picking_id', 'in', self.ids),
                ('state', '!=', 'done')
            ],
            'context': dict(
                self.env.context,
                picking_to_wave=self.ids,
                active_wave_id=self.env.context.get('active_wave_id').id,
                search_default_by_location=True,
            )}

    def _should_show_transfers(self):
        if len(self.batch_id) == 1 and self == self.batch_id.picking_ids:
            return False
        return super()._should_show_transfers()

    def _package_move_lines(self, batch_pack=False):
        if batch_pack:
            return super(StockPicking, self.batch_id.picking_ids if self.batch_id else self)._package_move_lines(batch_pack)
        return super()._package_move_lines(batch_pack)
