# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockPickingToWave(models.TransientModel):
    _name = 'stock.add.to.wave'
    _description = 'Wave Transfer Lines'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'stock.move.line':
            lines = self.env['stock.move.line'].browse(self.env.context.get('active_ids'))
            res['line_ids'] = self.env.context.get('active_ids')
            picking_types = lines.picking_type_id
        elif self.env.context.get('active_model') == 'stock.picking':
            pickings = self.env['stock.picking'].browse(self.env.context.get('active_ids'))
            res['picking_ids'] = self.env.context.get('active_ids')
            picking_types = pickings.picking_type_id
        else:
            return res

        if len(picking_types) > 1:
            raise UserError(_("The selected transfers should belong to the same operation type"))
        return res

    wave_id = fields.Many2one('stock.picking.batch', string='Wave Transfer', domain="[('is_wave', '=', True), ('state', '!=', 'done')]")
    picking_ids = fields.Many2many('stock.picking')
    line_ids = fields.Many2many('stock.move.line')
    mode = fields.Selection([('existing', 'an existing wave transfer'), ('new', 'a new wave transfer')], default='existing')
    user_id = fields.Many2one('res.users', string='Responsible', help='Person responsible for this wave transfer')


    def attach_pickings(self):
        self.ensure_one()

        self = self.with_context(active_owner_id=self.user_id.id)
        if self.line_ids:
            company = self.line_ids.company_id
            if len(company) > 1:
                raise UserError(_("The selected operations should belong to a unique company."))
            return self.line_ids._add_to_wave(self.wave_id)
        if self.picking_ids:
            company = self.picking_ids.company_id
            if len(company) > 1:
                raise UserError(_("The selected transfers should belong to a unique company."))
        else:
            raise UserError(_('Cannot create wave transfers'))

        view = self.env.ref('stock_picking_batch.view_move_line_tree_detailed_wave')
        return {
            'name': _('Add Operations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'views': [(view.id, 'tree')],
            'res_model': 'stock.move.line',
            'target': 'new',
            'domain': [
                ('picking_id', 'in', self.picking_ids.ids),
                ('state', '!=', 'done')
            ],
            'context': dict(
                self.env.context,
                picking_to_wave=self.picking_ids.ids,
                active_wave_id=self.wave_id.id,
            )}
