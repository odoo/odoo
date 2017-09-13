# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _inherit = ['mail.thread']
    _name = "stock.picking.batch"
    _description = "Batch Picking"
    _order = "name desc"

    name = fields.Char(
        string='Batch Picking Name', default='New',
        copy=False, required=True,
        help='Name of the batch picking')
    user_id = fields.Many2one(
        'res.users', string='Responsible', track_visibility='onchange',
        help='Person responsible for this batch picking')
    picking_ids = fields.One2many(
        'stock.picking', 'batch_id', string='Pickings',
        help='List of picking associated to this batch')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'Running'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], default='draft',
        copy=False, track_visibility='onchange', required=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('picking.batch') or '/'
        return super(StockPickingBatch, self).create(vals)

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
            raise UserError(_('Some pickings are still waiting for goods. Please check or force their availability before setting this batch to done.'))
        for picking in pickings:
            picking.message_post(
                body="<b>%s:</b> %s <a href=#id=%s&view_type=form&model=stock.picking.batch>%s</a>" % (
                    _("Transferred by"),
                    _("Batch Picking"),
                    picking.batch_id.id,
                    picking.batch_id.name))
        if pickings:
            pickings.action_done()
        return self.write({'state': 'done'})

    def _track_subtype(self, init_values):
        if 'state' in init_values:
            return 'stock_picking_batch.mt_batch_state'
        return super(StockPickingBatch, self)._track_subtype(init_values)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    batch_id = fields.Many2one(
        'stock.picking.batch', string='Batch Picking', oldname="wave_id",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help='Batch associated to this picking')
