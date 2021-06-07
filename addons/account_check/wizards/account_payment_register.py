# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    check_id = fields.Many2one('account.check', string='Check')
    check_type = fields.Char(compute='_compute_check_type')
    available_check_ids = fields.Many2many('account.check', compute='_compute_check_data')
    amount = fields.Monetary(compute='_compute_amount', readonly=False, store=True)
    payment_method_code = fields.Char(
        related='payment_method_id.code',
        help="Technical field used to adapt the interface to the payment type selected.")

    @api.depends('payment_method_code', 'partner_id', 'check_type', 'journal_id')
    def _compute_check_data(self):
        for rec in self:
            available_checks = rec.env['account.check']
            if not rec.check_type:
                rec.available_check_ids = available_checks
                continue
            operation, domain = self.env['account.payment']._get_checks_operations_model(
                self.payment_method_code, self.payment_type, False, self.journal_id)
            if domain:
                available_checks = available_checks.search(domain)
            rec.available_check_ids = available_checks

    @api.depends('payment_method_code')
    def _compute_check_type(self):
        """ Method to """
        for rec in self:
            if rec.payment_method_code in ['new_third_checks', 'out_third_checks', 'in_third_checks']:
                rec.check_type = 'third_check'
            elif rec.payment_method_code in ['new_own_checks', 'in_own_checks']:
                rec.check_type = 'own_check'
            else:
                rec.check_type = False

    @api.depends('check_id.amount', 'check_type')
    def _compute_amount(self):
        for rec in self.filtered('check_id'):
            rec.amount = rec.check_id.amount

    def _create_payment_vals_from_wizard(self):
        vals = super()._create_payment_vals_from_wizard()
        vals['check_id'] = self.check_id.id
        return vals
