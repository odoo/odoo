# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    check_ids = fields.One2many('quality.check', 'picking_id', 'Checks')
    quality_check_todo = fields.Boolean('Pending checks', compute='_compute_check')
    quality_check_fail = fields.Boolean(compute='_compute_check')
    quality_alert_ids = fields.One2many('quality.alert', 'picking_id', 'Alerts')
    quality_alert_count = fields.Integer(compute='_compute_quality_alert_count')

    def _compute_check(self):
        for picking in self:
            todo = False
            fail = False
            checkable_products = picking.mapped('move_line_ids').mapped('product_id')
            for check in picking.check_ids:
                if check.quality_state == 'none' and (check.product_id in checkable_products or check.measure_on == 'operation'):
                    todo = True
                elif check.quality_state == 'fail':
                    fail = True
                if fail and todo:
                    break
            picking.quality_check_fail = fail
            picking.quality_check_todo = todo

    def _compute_quality_alert_count(self):
        for picking in self:
            picking.quality_alert_count = len(picking.quality_alert_ids)

    @api.depends('quality_check_todo')
    def _compute_show_validate(self):
        super()._compute_show_validate()
        for picking in self:
            if picking.quality_check_todo:
                picking.show_validate = False

    def check_quality(self):
        self.ensure_one()
        checkable_products = self.mapped('move_line_ids').mapped('product_id')
        checks = self.check_ids.filtered(lambda check: check.quality_state == 'none' and (check.product_id in checkable_products or check.measure_on == 'operation'))
        if checks:
            return checks.action_open_quality_check_wizard()
        return False

    def _create_backorder(self):
        res = super(StockPicking, self)._create_backorder()
        if self.env.context.get('skip_check'):
            return res
        for backorder in res:
            backorder.move_line_ids.check_ids.picking_id = backorder
            backorder.backorder_id.check_ids.filtered(lambda qc: qc.quality_state == 'none').sudo().unlink()
            backorder.move_ids._create_quality_checks()
        return res

    def _action_done(self):
        if self._check_for_quality_checks():
            raise UserError(_('You still need to do the quality checks!'))
        return super(StockPicking, self)._action_done()

    def _pre_action_done_hook(self):
        res = super()._pre_action_done_hook()
        if res is True:
            pickings_to_check_quality = self._check_for_quality_checks()
            if pickings_to_check_quality:
                return pickings_to_check_quality[0].with_context(pickings_to_check_quality=pickings_to_check_quality.ids).check_quality()
        return res

    def _check_for_quality_checks(self):
        quality_pickings = self.env['stock.picking']
        for picking in self:
            product_to_check = picking.mapped('move_line_ids').filtered(lambda ml: ml.picked).mapped('product_id')
            if picking.mapped('check_ids').filtered(lambda qc: qc.quality_state == 'none' and (qc.product_id in product_to_check or qc.measure_on == 'operation')):
                quality_pickings |= picking
        return quality_pickings

    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        self.sudo().mapped('check_ids').filtered(lambda x: x.quality_state == 'none').unlink()
        return res

    def action_open_quality_check_picking(self):
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_check_action_picking")
        action['context'] = self.env.context.copy()
        action['context'].update({
            'search_default_picking_id': [self.id],
            'default_picking_id': self.id,
            'show_lots_text': self.show_lots_text,
        })
        return action

    def button_quality_alert(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_alert_action_check")
        action['views'] = [(False, 'form')]
        action['context'] = {
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_picking_id': self.id,
        }
        return action

    def open_quality_alert_picking(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_alert_action_check")
        action['context'] = {
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_picking_id': self.id,
        }
        action['domain'] = [('id', 'in', self.quality_alert_ids.ids)]
        action['views'] = [(False, 'tree'),(False,'form')]
        if self.quality_alert_count == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.quality_alert_ids.id
        return action
