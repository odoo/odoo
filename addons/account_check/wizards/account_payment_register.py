# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    check_ids = fields.One2many('account.payment.register.withholding', 'payment_register_id', string="Withholdings", compute='_compute_withholdings', readonly=False, store=True)
    # TODO this should be improoved. Check task for more information
    check_ids = fields.Many2many(
        'account.check', string='Checks', compute='_compute_checks',
    )
    new_check_ids = fields.Many2many('account.check', 'account_payment_register_check_rel', string='Checks ')
    select_check_ids = fields.Many2many('account.check', 'account_payment_register_check_rel2', string='Checks  ')

    @api.depends('select_check_ids', 'new_check_ids')
    def _compute_checks(self):
        for rec in self:
            rec.check_ids = rec.new_check_ids + rec.select_check_ids
    # this fields is to help with code and view but if needed this field could be removed and check everywhere for the payment_method_code
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

    @api.depends('check_ids.amount', 'check_type', 'select_check_ids.amount')
    def _compute_amount(self):
        for rec in self.filtered('check_type'):
            # TODO when fixed and no needed anymore select_check_ids change here
            rec.amount = sum((rec.check_ids | rec.select_check_ids).mapped('amount'))

    # net_amount = fields.Monetary(compute='_compute_net_amount', help="Net amount after withholdings")

    # @api.depends('line_ids')
    # def _compute_withholdings(self):
    #     for rec in self:
    #         # pass
    #         rec.write({'withholding_ids': [(5, 0, 0)] + [
    #             (0, 0, {'tax_id': x.id, 'name': '/'}) for x in self.env['account.tax'].search(
    #                 [('company_id', '=', rec.company_id.id), ('type_tax_use', '=', rec.partner_type)])]})

    # @api.depends('withholding_ids.amount', 'amount')
    # def _compute_net_amount(self):
    #     for rec in self:
    #         rec.net_amount = rec.amount - sum(rec.withholding_ids.mapped('amount'))

    # # TODO implement here instead on _create_payments
    # # def _create_payment_vals_from_wizard(self):
    # #     payment_vals = super()._create_payment_vals_from_wizard()
    # #     if self.withholding_ids:
    # #         payment_vals['withholding_vals'] = [{
    # #             'name': line.name,
    # #             'amount': line.amount,
    # #             'account_id': 5,
    # #             'tax_base_amount': line.base_amount,
    # #             'tax_id': line.tax_id.id,
    # #         } for line in self.withholding_ids]
    # #     return payment_vals

    # def _create_payments(self):
    #     payments = super()._create_payments()
    #     if self.withholding_ids:
    #         for payment in payments.with_context(check_move_validity=False):
    #             liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
    #             line_ids = []
    #             for line in self.withholding_ids:
    #                 line_ids += [(0, 0, payment._prepare_withholding_line_vals(line.tax_id, line.amount, line.base_amount, line.name))]
    #             liquidity_lines.debit = self.net_amount

    #             # TODO remove this hack when creating withholdings properly
    #             counterpart_lines.parent_state = 'draft'
    #             counterpart_lines.tax_ids = self.withholding_ids.mapped('tax_id')
    #             counterpart_lines.parent_state = 'posted'

    #             payment.move_id.write({'line_ids': line_ids})
    #     return payments
