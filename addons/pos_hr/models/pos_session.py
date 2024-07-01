# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        config_id = self.env['pos.config'].browse(config_id)
        if config_id.module_pos_hr:
            data += ['hr.employee']
        return data

    def _aggregate_payments_amounts_by_employee(self, payments):
        payments_by_employee = {}

        for employee, payments in payments.grouped('employee_id').items():
            payments_by_employee[employee.id] = {
                'id': employee.id,
                'name': employee.name,
                'amount': sum(payments.mapped('amount')),
            }

        return sorted(payments_by_employee.values(), key=lambda p: p['name'])

    def _aggregate_moves_by_employee(self):
        moves_per_employee = {}
        for employee, moves in self.sudo().statement_line_ids.grouped('employee_id').items():
            moves_per_employee[employee.id] = {
                'id': employee.id,
                'name': employee.name,
                'amount': sum(moves.mapped('amount')),
            }

        return sorted(moves_per_employee.values(), key=lambda p: -p['amount'])

    def get_closing_control_data(self):
        data = super().get_closing_control_data()

        orders = self._get_closed_orders()
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        cash_payment_method_ids = self.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
        default_cash_payment_method_id = cash_payment_method_ids[0] if cash_payment_method_ids else None
        default_cash_payments = payments.filtered(lambda p: p.payment_method_id == default_cash_payment_method_id) if default_cash_payment_method_id else []
        non_cash_payment_method_ids = self.payment_method_ids - default_cash_payment_method_id if default_cash_payment_method_id else self.payment_method_ids
        non_cash_payments_grouped_by_method_id = {pm.id: orders.payment_ids.filtered(lambda p: p.payment_method_id == pm) for pm in non_cash_payment_method_ids}

        data['default_cash_details']['amount_per_employee'] = self._aggregate_payments_amounts_by_employee(default_cash_payments)
        for payment_method in data['non_cash_payment_methods']:
            payment_method['amount_per_employee'] = self._aggregate_payments_amounts_by_employee(non_cash_payments_grouped_by_method_id[payment_method['id']])

        data['default_cash_details']['moves_per_employee'] = self._aggregate_moves_by_employee()

        return data

    def _prepare_account_bank_statement_line_vals(self, session, sign, amount, reason, extras):
        vals = super()._prepare_account_bank_statement_line_vals(session, sign, amount, reason, extras)
        vals['employee_id'] = extras['employee_id']
        return vals
