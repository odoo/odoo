# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPickingBatch(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = "stock.picking.batch"
    _description = "Batch Transfer"
    _order = "name desc"

    name = fields.Char(
        string='Batch Transfer', default='New',
        copy=False, required=True, readonly=True,
        help='Name of the batch transfer')
    user_id = fields.Many2one(
        'res.users', string='Responsible', tracking=True, check_company=True,
        help='Person responsible for this batch transfer')
    company_id = fields.Many2one(
        'res.company', string="Company", required=True, readonly=True,
        index=True, default=lambda self: self.env.company)
    picking_ids = fields.One2many(
        'stock.picking', 'batch_id', string='Transfers',
        domain="[('company_id', '=', company_id), ('state', 'not in', ('done', 'cancel'))]",
        help='List of transfers associated to this batch')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], default='draft',
        copy=False, tracking=True, required=True, readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('picking.batch') or '/'
        return super(StockPickingBatch, self).create(vals)

    def confirm_picking(self):
        self._check_company()
        pickings_todo = self.mapped('picking_ids')
        self.write({'state': 'in_progress'})
        return pickings_todo.action_assign()

    def cancel_picking(self):
        self.mapped('picking_ids').action_cancel()
        return self.write({'state': 'cancel'})

    def print_picking(self):
        pickings = self.mapped('picking_ids')
        if not pickings:
            raise UserError(_('Nothing to print.'))
        return self.env.ref('stock_picking_batch.action_report_picking_batch').report_action(self)

    def done(self):
        self._check_company()
        pickings = self.mapped('picking_ids').filtered(lambda picking: picking.state not in ('cancel', 'done'))
        if any(picking.state not in ('assigned') for picking in pickings):
            raise UserError(_('Some transfers are still waiting for goods. Please check or force their availability before setting this batch to done.'))
        for picking in pickings:
            picking.message_post(
                body="<b>%s:</b> %s <a href=#id=%s&view_type=form&model=stock.picking.batch>%s</a>" % (
                    _("Transferred by"),
                    _("Batch Transfer"),
                    picking.batch_id.id,
                    picking.batch_id.name))

        self.write({'state': 'done'})
        return self.picking_ids.button_validate()

    def _track_subtype(self, init_values):
        if 'state' in init_values:
            return self.env.ref('stock_picking_batch.mt_batch_state')
        return super(StockPickingBatch, self)._track_subtype(init_values)

