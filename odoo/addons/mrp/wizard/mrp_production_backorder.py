# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpProductionBackorderLine(models.TransientModel):
    _name = 'mrp.production.backorder.line'
    _description = "Backorder Confirmation Line"

    mrp_production_backorder_id = fields.Many2one('mrp.production.backorder', 'MO Backorder', required=True, ondelete="cascade")
    mrp_production_id = fields.Many2one('mrp.production', 'Manufacturing Order', required=True, ondelete="cascade", readonly=True)
    to_backorder = fields.Boolean('To Backorder')


class MrpProductionBackorder(models.TransientModel):
    _name = 'mrp.production.backorder'
    _description = "Wizard to mark as done or create back order"

    mrp_production_ids = fields.Many2many('mrp.production')

    mrp_production_backorder_line_ids = fields.One2many(
        'mrp.production.backorder.line',
        'mrp_production_backorder_id',
        string="Backorder Confirmation Lines")
    show_backorder_lines = fields.Boolean("Show backorder lines", compute="_compute_show_backorder_lines")

    @api.depends('mrp_production_backorder_line_ids')
    def _compute_show_backorder_lines(self):
        for wizard in self:
            wizard.show_backorder_lines = len(wizard.mrp_production_backorder_line_ids) > 1

    def action_close_mo(self):
        ctx = dict(self.env.context)
        always_backorder_mo_ids = ctx.pop('always_backorder_mo_ids', [])
        return self.mrp_production_ids.with_context(ctx, skip_backorder=True, mo_ids_to_backorder=always_backorder_mo_ids).button_mark_done()

    def action_backorder(self):
        ctx = dict(self.env.context)
        ctx.pop('default_mrp_production_ids', None)
        always_backorder_mo_ids = ctx.pop('always_backorder_mo_ids', [])
        mo_ids_to_backorder = self.mrp_production_backorder_line_ids.filtered(lambda l: l.to_backorder).mrp_production_id.ids + always_backorder_mo_ids
        return self.mrp_production_ids.with_context(ctx, skip_backorder=True, mo_ids_to_backorder=mo_ids_to_backorder).button_mark_done()
