# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    mo_analytic_account_line_ids = fields.Many2many('account.analytic.line', 'mrp_workorder_mo_analytic_rel', copy=False)
    wc_analytic_account_line_ids = fields.Many2many('account.analytic.line', 'mrp_workorder_wc_analytic_rel', copy=False)

    def _compute_duration(self):
        res = super()._compute_duration()
        self._create_or_update_analytic_entry()
        return res

    def _set_duration(self):
        res = super()._set_duration()
        self._create_or_update_analytic_entry()
        return res

    def action_cancel(self):
        (self.mo_analytic_account_line_ids | self.wc_analytic_account_line_ids).unlink()
        return super().action_cancel()

    def _prepare_analytic_line_values(self, account_field_values, amount, unit_amount):
        self.ensure_one()
        return {
            'name': _("[WC] %s", self.display_name),
            'amount': amount,
            **account_field_values,
            'unit_amount': unit_amount,
            'product_id': self.product_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_hour').id,
            'company_id': self.company_id.id,
            'ref': self.production_id.name,
            'category': 'manufacturing_order',
        }

    def _create_or_update_analytic_entry(self):
        for wo in self:
            if not wo.id:
                continue
            hours = wo.duration / 60.0
            value = -hours * wo.workcenter_id.costs_hour
            wo._create_or_update_analytic_entry_for_record(value, hours)

    def _create_or_update_analytic_entry_for_record(self, value, hours):
        self.ensure_one()
        if self.workcenter_id.analytic_distribution or self.wc_analytic_account_line_ids or self.mo_analytic_account_line_ids:
            wc_analytic_line_vals = self.env['account.analytic.account']._perform_analytic_distribution(self.workcenter_id.analytic_distribution, value, hours, self.wc_analytic_account_line_ids, self)
            if wc_analytic_line_vals:
                self.wc_analytic_account_line_ids += self.env['account.analytic.line'].sudo().create(wc_analytic_line_vals)

    def unlink(self):
        (self.mo_analytic_account_line_ids | self.wc_analytic_account_line_ids).unlink()
        return super().unlink()
