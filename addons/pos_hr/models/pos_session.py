# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.tools import plaintext2html


class PosSession(models.Model):
    _inherit = 'pos.session'
    employee_id = fields.Many2one(
        "hr.employee",
        string="Cashier",
        help="The employee who currently uses the cash register",
        tracking=True,
    )
    logged_employee_ids = fields.Many2many(
        'hr.employee',
        string="Logged In Cashiers",
        store=True,
        compute='_compute_logged_employee_ids',
        help="All employees who have logged into this session",
    )

    @api.depends('employee_id')
    def _compute_logged_employee_ids(self):
        for session in self:
            employee = session.employee_id
            if employee and employee.id not in session.logged_employee_ids.ids:
                session.logged_employee_ids |= employee

    @api.model
    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        if config.module_pos_hr:
            data += ['hr.employee']
        return data

    def _set_opening_control_data(self, cashbox_value: int, notes: str):
        super()._set_opening_control_data(cashbox_value, notes)
        if self.employee_id:
            self.message_post(body=plaintext2html(_('Opened register')), author_id=self._get_message_author().id)

    def _get_message_author(self):
        if self.employee_id:
            if related_partners := self.employee_id._get_related_partners():
                return related_partners[0]

        return super()._get_message_author()

    def _aggregate_payments_amounts_by_employee(self, all_payments):
        payments_by_employee = []

        for employee, payments_group in all_payments.grouped('employee_id').items():
            payments_by_employee.append({
                'id': employee.id if employee else 'others',
                'name': employee.name if employee else _('Others'),
                'amount': sum(payments_group.mapped('amount')),
            })

        # Sort such that "Others" is always the last item
        return sorted(
            payments_by_employee,
            key=lambda p: (p['id'] == 'others', p['name'])
        )

    def get_closing_control_data(self):
        data = super().get_closing_control_data()
        if not self.config_id.module_pos_hr or not data['default_cash_details']:
            return data

        orders = self._get_closed_orders()
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        default_cash_payment_method_id = data['default_cash_details']['id']
        default_cash_payments = payments.filtered(lambda p: p.payment_method_id.id == default_cash_payment_method_id) if default_cash_payment_method_id else self.env['pos.payment']
        data['default_cash_details']['cash_breakdown']['amount_per_employee'] = self._aggregate_payments_amounts_by_employee(default_cash_payments)
        return data

    def _prepare_account_bank_statement_line_vals(self, session, sign, amount, reason, partner_id, extras):
        vals = super()._prepare_account_bank_statement_line_vals(session, sign, amount, reason, partner_id, extras)
        if extras.get('employee_id'):
            vals['employee_id'] = extras['employee_id']
        return vals

    def get_cash_in_out_list(self):
        cash_in_out_list = super().get_cash_in_out_list()
        if self.config_id.module_pos_hr:
            for cash_in_out in cash_in_out_list:
                cash_move = self.env['account.bank.statement.line'].browse(cash_in_out['id'])
                if cash_move.employee_id:
                    cash_in_out['cashier_name'] = cash_move.partner_id.name
        return cash_in_out_list
