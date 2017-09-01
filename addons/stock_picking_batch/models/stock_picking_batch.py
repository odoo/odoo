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
        return self.env.ref('stock_picking_batch.action_report_picking_batch').report_action(self)

    @api.multi
    def done(self):
        pickings = self.mapped('picking_ids').filtered(lambda picking: picking.state not in ('cancel', 'done'))
        if any(picking.state not in ('assigned') for picking in pickings):
            raise UserError(_('Some pickings are still waiting for goods. Please check or force their availability before setting this batch to done.'))
        for picking in pickings:
            picking.message_post(
                body="<b>%s:</b> %s <a href=#id=%s&view_type=form&model=stock.picking.batch>%s</a>" % (
                    _("Transferred by"),
                    _("Batch Picking"),
                    picking.batch_id.id,
                    picking.batch_id.name))

        picking_to_backorder = self.env['stock.picking']
        picking_without_qty_done = self.env['stock.picking']
        for picking in pickings:
            if all([x.qty_done == 0.0 for x in picking.move_line_ids]):
                # If no lots when needed, raise error
                picking_type = picking.picking_type_id
                if (picking_type.use_create_lots or picking_type.use_existing_lots):
                    for ml in picking.move_line_ids:
                        if ml.product_id.tracking != 'none':
                            raise UserError(_('Some products require lots/serial numbers.'))
                # Check if we need to set some qty done.
                picking_without_qty_done |= picking
            elif picking._check_backorder():
                picking_to_backorder |= picking
            else:
                picking.action_done()
        self.write({'state': 'done'})
        if picking_without_qty_done:
            view = self.env.ref('stock.view_immediate_transfer')
            wiz = self.env['stock.immediate.transfer'].create({
                'pick_ids': [(4, p.id) for p in picking_without_qty_done],
                'pick_to_backorder_ids': [(4, p.id) for p in picking_to_backorder],
            })
            return {
                'name': _('Immediate Transfer?'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.immediate.transfer',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context,
            }
        if picking_to_backorder:
            return picking_to_backorder.action_generate_backorder_wizard()
        return True

    def _track_subtype(self, init_values):
        if 'state' in init_values:
            return 'stock_picking_batch.mt_batch_state'
        return super(StockPickingBatch, self)._track_subtype(init_values)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    batch_id = fields.Many2one(
        'stock.picking.batch', string='Batch Picking', oldname="wave_id",
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help='Batch associated to this picking', copy=False)
