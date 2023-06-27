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
    first_qty = fields.Float(string="Quantity", compute="_compute_first_qty", store=True, readonly=False)
    second_qty = fields.Float(compute="_compute_second_qty", store=True, readonly=False)
    valid_details = fields.Boolean("Valid", compute="_compute_valid_details")

    @api.depends("production_capacity", "product_qty")
    def _compute_first_qty(self):
        for wizard in self:
            if wizard.first_qty:
                continue
            if wizard.production_capacity and wizard.product_qty > wizard.production_capacity:
                wizard.first_qty = wizard.production_capacity
            else:
                wizard.first_qty = wizard.product_qty / 2

    @api.depends('first_qty')
    def _compute_second_qty(self):
        for wizard in self:
            wizard.second_qty = float_round(wizard.product_qty - wizard.first_qty, precision_rounding=wizard.product_uom_id.rounding)

    @api.depends('first_qty', 'second_qty')
    def _compute_valid_details(self):
        for wizard in self:
            wizard.valid_details = wizard.first_qty and wizard.second_qty and float_compare(wizard.product_qty, wizard.first_qty + wizard.second_qty, precision_rounding=wizard.product_uom_id.rounding) == 0

    def action_split(self):
        self.production_id._split_productions({self.production_id: [self.first_qty, self.second_qty]})
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
        action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_split_multi')
        action['res_id'] = self.production_split_multi_id.id
        return action
