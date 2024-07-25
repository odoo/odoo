# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.tools import float_is_zero


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    mo_analytic_account_line_id = fields.Many2one('account.analytic.line', copy=False)
    wc_analytic_account_line_id = fields.Many2one('account.analytic.line', copy=False)

    def _compute_duration(self):
        res = super()._compute_duration()
        self._create_or_update_analytic_entry()
        return res

    def _set_duration(self):
        res = super()._set_duration()
        self._create_or_update_analytic_entry()
        return res

    def action_cancel(self):
        (self.mo_analytic_account_line_id | self.wc_analytic_account_line_id).unlink()
        return super().action_cancel()

    def _prepare_analytic_line_values(self, account, unit_amount, amount):
        self.ensure_one()
        return {
            'name': _("[WC] %s", self.display_name),
            'amount': amount,
            'account_id': account.id,
            'unit_amount': unit_amount,
            'product_id': self.product_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_hour').id,
            'company_id': self.company_id.id,
            'ref': self.production_id.name,
            'category': 'manufacturing_order',
        }

    def _create_or_update_analytic_entry(self):
        wo_to_link_mo_analytic_line = self.env['mrp.workorder']
        wo_to_link_wc_analytic_line = self.env['mrp.workorder']
        mo_analytic_line_vals_list = []
        wc_analytic_line_vals_list = []
        for wo in self.filtered(lambda wo: wo.production_id.analytic_account_id or wo.workcenter_id.costs_hour_account_id):
            hours = wo.duration / 60.0
            value = -hours * wo.workcenter_id.costs_hour
            mo_account = wo.production_id.analytic_account_id
            wc_account = wo.workcenter_id.costs_hour_account_id
            if mo_account:
                mo_currency = mo_account.currency_id or wo.company_id.currency_id
                is_zero = float_is_zero(value, precision_rounding=mo_currency.rounding)
                if wo.mo_analytic_account_line_id:
                    wo.mo_analytic_account_line_id.write({
                        'unit_amount': hours,
                        'amount': value if not is_zero else 0,
                    })
                elif not is_zero:
                    wo_to_link_mo_analytic_line += wo
                    mo_analytic_line_vals_list.append(wo._prepare_analytic_line_values(mo_account, hours, value))
            if wc_account and wc_account != mo_account:
                wc_currency = wc_account.currency_id or wo.company_id.currency_id
                is_zero = float_is_zero(value, precision_rounding=wc_currency.rounding)
                if wo.wc_analytic_account_line_id:
                    wo.wc_analytic_account_line_id.write({
                        'unit_amount': hours,
                        'amount': value if not is_zero else 0,
                    })
                elif not is_zero:
                    wo_to_link_wc_analytic_line += wo
                    wc_analytic_line_vals_list.append(wo._prepare_analytic_line_values(wc_account, hours, value))
        analytic_lines = self.env['account.analytic.line'].sudo().create(mo_analytic_line_vals_list + wc_analytic_line_vals_list)
        mo_analytic_lines, wc_analytic_lines = analytic_lines[:len(wo_to_link_mo_analytic_line)], analytic_lines[len(wo_to_link_mo_analytic_line):]
        for wo, analytic_line in zip(wo_to_link_mo_analytic_line, mo_analytic_lines):
            wo.mo_analytic_account_line_id = analytic_line
        for wo, analytic_line in zip(wo_to_link_wc_analytic_line, wc_analytic_lines):
            wo.wc_analytic_account_line_id = analytic_line

    def unlink(self):
        (self.mo_analytic_account_line_id | self.wc_analytic_account_line_id).unlink()
        return super().unlink()
