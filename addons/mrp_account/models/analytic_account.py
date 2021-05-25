# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    production_ids = fields.One2many('mrp.production', 'analytic_account_id', string='Manufacturing Orders')
    production_count = fields.Integer("Manufacturing Orders Count", compute='_compute_production_count')
    bom_ids = fields.One2many('mrp.bom', 'analytic_account_id', string='Bills of Materials')
    bom_count = fields.Integer("BoM Count", compute='_compute_bom_count')
    workcenter_ids = fields.One2many('mrp.workcenter', 'costs_hour_account_id', string='Workcenters')
    workorder_count = fields.Integer("Work Order Count", compute='_compute_workorder_count')

    @api.depends('production_ids')
    def _compute_production_count(self):
        for account in self:
            account.production_count = len(account.production_ids)

    @api.depends('bom_ids')
    def _compute_bom_count(self):
        for account in self:
            account.bom_count = len(account.bom_ids)

    @api.depends('workcenter_ids.order_ids', 'production_ids.workorder_ids')
    def _compute_workorder_count(self):
        for account in self:
            account.workorder_count = len(account.workcenter_ids.order_ids | account.production_ids.workorder_ids)

    def action_view_mrp_production(self):
        self.ensure_one()
        result = {
            "type": "ir.actions.act_window",
            "res_model": "mrp.production",
            "domain": [['id', 'in', self.production_ids.ids]],
            "name": "Manufacturing Orders",
            'view_mode': 'tree,form',
            "context": {'default_analytic_account_id': self.id},
        }
        if len(self.production_ids) == 1:
            result['view_mode'] = 'form'
            result['res_id'] = self.production_ids.id
        return result

    def action_view_mrp_bom(self):
        self.ensure_one()
        result = {
            "type": "ir.actions.act_window",
            "res_model": "mrp.bom",
            "domain": [['id', 'in', self.bom_ids.ids]],
            "name": "Bills of Materials",
            'view_mode': 'tree,form',
            "context": {'default_analytic_account_id': self.id},
        }
        if self.bom_count == 1:
            result['view_mode'] = 'form'
            result['res_id'] = self.bom_ids.id
        return result

    def action_view_workorder(self):
        self.ensure_one()
        result = {
            "type": "ir.actions.act_window",
            "res_model": "mrp.workorder",
            "domain": [['id', 'in', (self.workcenter_ids.order_ids | self.production_ids.workorder_ids).ids]],
            "context": {"create": False},
            "name": "Work Orders",
            'view_mode': 'tree',
        }
        return result


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    category = fields.Selection(selection_add=[('manufacturing_order', 'Manufacturing Order')])
