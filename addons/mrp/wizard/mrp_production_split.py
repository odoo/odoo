# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, Command
from odoo.tools import float_round, float_compare
from odoo.exceptions import UserError


class MrpProductionSplitMulti(models.TransientModel):
    _description = "Wizard to Split Multiple Productions"

    production_ids = fields.One2many('mrp.production.split', 'production_split_multi_id', 'Productions To Split')


class MrpProductionSplit(models.TransientModel):
    _description = "Wizard to Split a Production"

    production_split_multi_id = fields.Many2one('mrp.production.split.multi', 'Split Productions')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', readonly=True)
    product_id = fields.Many2one(related='production_id.product_id')
    product_qty = fields.Float(related='production_id.product_qty')
    product_uom_id = fields.Many2one(related='production_id.product_uom_id')
    production_capacity = fields.Float(related='production_id.production_capacity')
    counter = fields.Integer(
        "Split #", default=2, compute="_compute_counter",
        store=True, readonly=False)
    production_detailed_vals_ids = fields.One2many(
        'mrp.production.split.line', 'mrp_production_split_id',
        'Split Details', compute="_compute_details", store=True, readonly=False)
    valid_details = fields.Boolean("Valid", compute="_compute_valid_details")
    split_pre_production_picking = fields.Boolean("Split Pre Production picking", default=True,
        help="When enabled, new split pre-production pickings will be created for each generated MO.")

    @api.depends('production_detailed_vals_ids')
    def _compute_counter(self):
        for wizard in self:
            wizard.counter = len(wizard.production_detailed_vals_ids)

    @api.depends('counter')
    def _compute_details(self):
        for wizard in self:
            commands = [Command.clear()]
            if wizard.counter < 1 or not wizard.production_id:
                wizard.production_detailed_vals_ids = commands
                continue
            quantity = float_round(wizard.product_qty / wizard.counter, precision_rounding=wizard.product_uom_id.rounding)
            remaining_quantity = wizard.product_qty
            for i in range(wizard.counter - 1):
                commands.append(Command.create({
                    'quantity': quantity,
                    'user_id': wizard.production_id.user_id,
                    'date': wizard.production_id.date_start,
                }))
                remaining_quantity = float_round(remaining_quantity - quantity, precision_rounding=wizard.product_uom_id.rounding)
            commands.append(Command.create({
                'quantity': remaining_quantity,
                'user_id': wizard.production_id.user_id,
                'date': wizard.production_id.date_start,
            }))
            wizard.production_detailed_vals_ids = commands

    @api.depends('production_detailed_vals_ids')
    def _compute_valid_details(self):
        self.valid_details = False
        for wizard in self:
            if wizard.production_detailed_vals_ids:
                wizard.valid_details = float_compare(wizard.product_qty, sum(wizard.production_detailed_vals_ids.mapped('quantity')), precision_rounding=wizard.product_uom_id.rounding) == 0

    def action_split(self):
        if self.split_pre_production_picking:
            picking = self.production_id.picking_ids
            if len(picking) > 1 or picking.state == "done":
                raise UserError(_("Cannot split pre-production picking: the pre-picking for this manufacturing order is already done."))

        productions = self.production_id.with_context(is_split_production=True, is_split_pre_picking=self.split_pre_production_picking)._split_productions({self.production_id: [detail.quantity for detail in self.production_detailed_vals_ids]})
        for production, detail in zip(productions, self.production_detailed_vals_ids):
            production.user_id = detail.user_id
            production.date_start = detail.date

        # Split the pre-production picking if `split_pre_production_picking` is set to True for that MO in 2-step or 3-step MRP process.
        if self.split_pre_production_picking and self.production_id.warehouse_id.manufacture_steps in ['pbm_sam', 'pbm']:
            # Adjust the demand(product_uom_qty) quantity of pre-picking for other manufacturing orders that share common pre-picking
            for picking_move in picking.move_ids:
                total_raw_qty = sum(move.product_uom_qty
                    for production in productions
                    for move in production.move_raw_ids
                    if move.product_id == picking_move.product_id
                    )
                picking_move.product_uom_qty = max(picking_move.product_uom_qty - total_raw_qty, 0)

            if all(qty == 0 for qty in picking.move_ids.mapped('product_uom_qty')) and len(picking) == 1:
                picking.action_cancel()
                picking.group_id = False
            else:
                picking.action_assign()

            for production in productions:
                production.write({'is_pre_production_picking_split': True})
                production.move_raw_ids.write({'move_orig_ids': False, 'state': 'draft'})
                production.write({'state': 'draft'})
                production.action_confirm()
                unlink_production_ids = production.picking_ids.mapped('move_ids.production_ids').filtered(lambda p: p == production).ids
                production.picking_ids.move_ids.write({
                    'production_ids': [(3, prod_id, False) for prod_id in unlink_production_ids]
                })

        if self.production_split_multi_id:
            saved_production_split_multi_id = self.production_split_multi_id.id
            self.production_split_multi_id.production_ids = [Command.unlink(self.id)]
            action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split_multi')
            action['res_id'] = saved_production_split_multi_id
            return action

    def action_prepare_split(self):
        action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split')
        action['res_id'] = self.id
        return action

    def action_return_to_list(self):
        self.production_detailed_vals_ids = [Command.clear()]
        self.counter = 0
        action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split_multi')
        action['res_id'] = self.production_split_multi_id.id
        return action


class MrpProductionSplitLine(models.TransientModel):
    _description = "Split Production Detail"

    mrp_production_split_id = fields.Many2one(
        'mrp.production.split', 'Split Production', required=True, ondelete="cascade")
    quantity = fields.Float('Quantity To Produce', digits='Product Unit of Measure', required=True)
    user_id = fields.Many2one(
        'res.users', 'Responsible',
        domain=lambda self: [('groups_id', 'in', self.env.ref('mrp.group_mrp_user').id)])
    date = fields.Datetime('Schedule Date')
