# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression
import ast


class ProductionLot(models.Model):
    _inherit = 'stock.lot'

    quality_check_qty = fields.Integer(compute='_compute_quality_check_qty', groups='quality.group_quality_user')
    quality_alert_qty = fields.Integer(compute='_compute_quality_alert_qty', groups='quality.group_quality_user')

    def _compute_quality_check_qty(self):
        for prod_lot in self:
            domain = expression.AND([self._get_quality_check_domain(prod_lot), [('company_id', '=', self.env.company.id)]])
            prod_lot.quality_check_qty = self.env['quality.check'].search_count(domain)

    def _get_quality_check_domain(self, prod_lot):
        return [('lot_id', '=', prod_lot.id)]

    def action_open_quality_checks(self):
        self.ensure_one()
        action_values = self.env['ir.actions.act_window']._for_xml_id('quality_control.quality_check_action_production_lot')
        domain = ast.literal_eval(action_values.get('domain')) if action_values.get('domain') else []
        action_values["domain"] = expression.AND([domain, self._get_quality_check_domain(self)])
        return action_values

    def _compute_quality_alert_qty(self):
        for prod_lot in self:
            prod_lot.quality_alert_qty = self.env['quality.alert'].search_count([
                ('lot_id', '=', prod_lot.id),
                ('company_id', '=', self.env.company.id)
            ])

    def action_lot_open_quality_alerts(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("quality_control.quality_alert_action_check")
        action.update({
            'domain': [('lot_id', '=', self.id)],
            'context': {
                'default_product_id': self.product_id.id,
                'default_lot_id': self.id,
                'default_company_id': self.company_id.id,
            },
        })
        return action
