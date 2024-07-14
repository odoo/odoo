# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductionLot(models.Model):
    _inherit = 'stock.lot'

    quality_check_qty = fields.Integer(compute='_compute_quality_check_qty', groups='quality.group_quality_user')
    quality_alert_qty = fields.Integer(compute='_compute_quality_alert_qty', groups='quality.group_quality_user')

    def _compute_quality_check_qty(self):
        for prod_lot in self:
            prod_lot.quality_check_qty = self.env['quality.check'].search_count([
                ('lot_id', '=', prod_lot.id),
                ('company_id', '=', self.env.company.id)
            ])

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
