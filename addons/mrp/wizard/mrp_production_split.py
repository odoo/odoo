# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command
from odoo.tools import float_round, float_compare


class MrpProductionSplitMulti(models.TransientModel):
    _name = 'mrp.production.split.multi'
    _description = "Wizard to Split Multiple Productions"

    production_ids = fields.One2many('mrp.production.split', 'production_split_multi_id', 'Productions To Split')


class MrpProductionSplit(models.TransientModel):
    _name = 'mrp.production.split'
    _description = "Wizard to Split a Production"

    production_split_multi_id = fields.Many2one('mrp.production.split.multi', 'Split Productions')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', readonly=True)
    product_id = fields.Many2one(related='production_id.product_id')
    product_qty = fields.Float(related='production_id.product_qty')
    product_uom_id = fields.Many2one(related='production_id.product_uom_id')
    production_capacity = fields.Float(related='production_id.production_capacity')
    tracking = fields.Selection(related='product_id.tracking')
    first_lot_name = fields.Char('First Lot/SN', compute='_compute_first_lot_name', readonly=False)
    counter = fields.Integer(
        "Split #", default=0, compute="_compute_counter",
        store=True, readonly=False)
    production_detailed_vals_ids = fields.One2many(
        'mrp.production.split.line', 'mrp_production_split_id',
        'Split Details', compute="_compute_details", store=True, readonly=False)
    valid_details = fields.Boolean("Valid", compute="_compute_valid_details")

    @api.depends('production_id.lot_producing_id')
    def _compute_first_lot_name(self):
        for wizard in self:
            wizard.first_lot_name = self.env.context.get('default_first_lot_name') or wizard.production_id.lot_producing_id.name

    @api.depends('production_detailed_vals_ids')
    def _compute_counter(self):
        for wizard in self:
            wizard.counter = len(wizard.production_detailed_vals_ids)

    @api.depends('counter', 'first_lot_name')
    def _compute_details(self):
        for wizard in self:
            commands = [Command.clear()]
            if wizard.counter < 1 or not wizard.production_id:
                wizard.production_detailed_vals_ids = commands
                continue
            quantity = float_round(wizard.product_qty / wizard.counter, precision_rounding=wizard.product_uom_id.rounding)
            remaining_quantity = wizard.product_qty
            should_generate_lot = wizard.product_id.tracking != 'none' and wizard.first_lot_name
            if should_generate_lot:
                lot_names = self.env['stock.lot'].generate_lot_names(wizard.first_lot_name, wizard.counter)
            for i in range(wizard.counter - 1):
                commands.append(Command.create({
                    'quantity': quantity,
                    'user_id': wizard.production_id.user_id,
                    'date': wizard.production_id.date_start,
                    'lot_names': lot_names[i] if should_generate_lot else False,
                }))
                remaining_quantity = float_round(remaining_quantity - quantity, precision_rounding=wizard.product_uom_id.rounding)
            commands.append(Command.create({
                'quantity': remaining_quantity,
                'user_id': wizard.production_id.user_id,
                'date': wizard.production_id.date_start,
                'lot_names': lot_names[-1] if should_generate_lot else False,
            }))
            wizard.production_detailed_vals_ids = commands

    @api.depends('production_detailed_vals_ids')
    def _compute_valid_details(self):
        self.valid_details = False
        for wizard in self:
            if wizard.production_detailed_vals_ids:
                wizard.valid_details = float_compare(wizard.product_qty, sum(wizard.production_detailed_vals_ids.mapped('quantity')), precision_rounding=wizard.product_uom_id.rounding) == 0

    def action_split(self):
        productions = self.production_id._split_productions(
            amounts={self.production_id: [detail.quantity for detail in self.production_detailed_vals_ids]},
            lot_names={self.production_id: [detail.lot_names for detail in self.production_detailed_vals_ids]},
        )
        for production, detail in zip(productions, self.production_detailed_vals_ids):
            production.user_id = detail.user_id
            production.date_start = detail.date
        if self.production_split_multi_id:
            saved_production_split_multi_id = self.production_split_multi_id.id
            self.production_split_multi_id.production_ids = [Command.unlink(self.id)]
            action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split_multi')
            action['res_id'] = saved_production_split_multi_id
            return action

    def action_prepare_split(self):
        action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split')
        action['res_id'] = self.id
        action['context'] = {
            'default_first_lot_name': self.first_lot_name,
        }
        return action

    def action_return_to_list(self):
        self.production_detailed_vals_ids = [Command.clear()]
        self.counter = 0
        action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split_multi')
        action['res_id'] = self.production_split_multi_id.id
        return action

    def action_generate_first_lot_name(self):
        first_lot_name = self.env['stock.lot']._get_next_serial(self.production_id.company_id, self.product_id) or self.env['ir.sequence'].next_by_code('stock.lot.serial')
        # return a new action since current wizard will be closed
        action = self.action_prepare_split()
        action['context'] = {
            'default_first_lot_name': first_lot_name,
        }
        return action


class MrpProductionSplitLine(models.TransientModel):
    _name = 'mrp.production.split.line'
    _description = "Split Production Detail"

    mrp_production_split_id = fields.Many2one(
        'mrp.production.split', 'Split Production', required=True, ondelete="cascade")
    quantity = fields.Float('Quantity To Produce', digits='Product Unit of Measure', required=True)
    user_id = fields.Many2one(
        'res.users', 'Responsible',
        domain=lambda self: [('groups_id', 'in', self.env.ref('mrp.group_mrp_user').id)])
    date = fields.Datetime('Schedule Date')
    lot_names = fields.Text('Lot/Serial Numbers')
