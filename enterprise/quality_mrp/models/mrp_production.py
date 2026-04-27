# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    check_ids = fields.One2many('quality.check', 'production_id', string="Checks")
    quality_check_todo = fields.Boolean(compute='_compute_check')
    quality_check_fail = fields.Boolean(compute='_compute_check')
    quality_alert_ids = fields.One2many('quality.alert', "production_id", string="Alerts")
    quality_alert_count = fields.Integer(compute='_compute_quality_alert_count')

    def _compute_quality_alert_count(self):
        for production in self:
            production.quality_alert_count = len(production.quality_alert_ids)

    def _compute_check(self):
        for production in self:
            todo = False
            fail = False
            for check in production.check_ids:
                if check.quality_state == 'none':
                    todo = True
                elif check.quality_state == 'fail':
                    fail = True
                if fail and todo:
                    break
            production.quality_check_fail = fail
            production.quality_check_todo = todo

    def button_quality_alert(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_alert_action_check")
        action['views'] = [(False, 'form')]
        action['context'] = {
            'default_company_id': self.company_id.id,
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_production_id': self.id,
        }
        return action

    def pre_button_mark_done(self):
        res = super().pre_button_mark_done()
        if isinstance(res, dict) and res.get('type') == 'ir.actions.act_window':
            return res
        is_qc_status_ok = self._check_qc_status()
        if not is_qc_status_ok and self.env.context.get('from_wizard'):
            return {'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('You still need to do the quality checks!'),
                    'next': {'type': 'ir.actions.act_window_close'},
                    'sticky': False,
                    'type': 'warning',
                }
            }
        elif not is_qc_status_ok:
            raise UserError(_('You still need to do the quality checks!'))
        return res

    def _check_qc_status(self):
        return 'none' not in self.check_ids.mapped('quality_state')

    def open_quality_alert_mo(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("quality_control.quality_alert_action_check")
        action['context'] = {
            'default_company_id': self.company_id.id,
            'default_product_id': self.product_id.id,
            'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
            'default_production_id': self.id,
            }
        action['domain'] = [('id', 'in', self.quality_alert_ids.ids)]
        action['views'] = [(False, 'list'), (False, 'form')]
        if self.quality_alert_count == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.quality_alert_ids.id
        return action

    def check_quality(self):
        self.ensure_one()
        if float_is_zero(self.qty_producing, precision_rounding=self.product_uom_id.rounding):
            raise UserError(_("You cannot perform a quality check if the quantity producing is zero. Please set the production quantity first."))
        checks = self.check_ids.filtered(lambda x: x.quality_state == 'none')
        if checks:
            return checks.action_open_quality_check_wizard()

    def action_cancel(self):
        res = super(MrpProduction, self).action_cancel()
        self.sudo().mapped('check_ids').filtered(lambda x: x.quality_state == 'none').unlink()
        return res

    def _action_confirm_mo_backorders(self):
        super()._action_confirm_mo_backorders()
        (self.move_raw_ids | self.move_finished_ids)._create_quality_checks_for_mo()

    def action_open_on_demand_quality_check(self):
        self.ensure_one()
        if self.state in ['draft', 'done', 'cancel']:
            raise UserError(_('You can not create quality check for a draft, done or cancelled manufacturing order.'))
        return {
            'name': _('On-Demand Quality Check'),
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check.on.demand',
            'views': [(self.env.ref('quality_control.quality_check_on_demand_view_form').id, 'form')],
            'target': 'new',
            'context': {
                'default_production_id': self.id,
                'on_demand_wizard': True,
            }
        }
