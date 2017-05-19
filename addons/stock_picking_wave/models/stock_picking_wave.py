# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPickingWave(models.Model):
    _inherit = ['mail.thread']
    _name = "stock.picking.wave"
    _description = "Picking Wave"
    _order = "name desc"

    name = fields.Char(
        string='Picking Wave Name', default='/',
        copy=False, required=True,
        help='Name of the picking wave')
    user_id = fields.Many2one(
        'res.users', string='Responsible', track_visibility='onchange',
        help='Person responsible for this wave')
    picking_ids = fields.One2many(
        'stock.picking', 'wave_id', string='Pickings',
        help='List of picking associated to this wave')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'Running'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], default='draft',
        copy=False, track_visibility='onchange', required=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('picking.wave') or '/'
        return super(StockPickingWave, self).create(vals)

    @api.multi
    def confirm_picking(self):
        pickings_todo = self.mapped('picking_ids')
        self.write({'state': 'in_progress'})
        return pickings_todo.action_assign()

    @api.multi
    def cancel_picking(self):
        self.mapped('picking_ids').action_cancel()
        return self.write({'state': 'cancel'})

    @api.multi
    def print_picking(self):
        pickings = self.mapped('picking_ids')
        if not pickings:
            raise UserError(_('Nothing to print.'))
        return self.env.ref('stock.action_report_picking').with_context(active_ids=pickings.ids, active_model='stock.picking').report_action([])

    @api.multi
    def done(self):
        pickings = self.mapped('picking_ids').filtered(lambda picking: picking.state not in ('cancel', 'done'))
        if any(picking.state != 'assigned' for picking in pickings):
            raise UserError(_('Some pickings are still waiting for goods. Please check or force their availability before setting this wave to done.'))
        for picking in pickings:
            picking.message_post(
                body="<b>%s:</b> %s <a href=#id=%s&view_type=form&model=stock.picking.wave>%s</a>" % (
                    _("Transferred by"),
                    _("Picking Wave"),
                    picking.wave_id.id,
                    picking.wave_id.name))
        if pickings:
            pickings.action_done()
        return self.write({'state': 'done'})

    def _track_subtype(self, init_values):
        if 'state' in init_values:
            return 'stock_picking_wave.mt_wave_state'
        return super(StockPickingWave, self)._track_subtype(init_values)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    wave_id = fields.Many2one(
        'stock.picking.wave', string='Picking Wave',
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help='Picking wave associated to this picking')
