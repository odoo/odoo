# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, fields, api, Command, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_main_payment = fields.Boolean(compute="_compute_is_main_payment", store=True)
    main_payment_id = fields.Many2one("account.payment.register")
    new_main_payment_id = fields.Many2one("account.payment")
    link_payment_ids = fields.One2many(comodel_name="account.payment.register", inverse_name="main_payment_id")
    payment_total = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_payment_total',
        store=True,
    )

    @api.depends("payment_method_line_id")
    def _compute_is_main_payment(self):
        for rec in self:
            rec.is_main_payment = rec.payment_method_line_id.payment_method_id.code == 'payment_bundle'

    @api.depends("main_payment_id")
    def _compute_available_journal_ids(self):
        """Only main payment can use the bundle journal"""
        super()._compute_available_journal_ids()
        for pay in self.filtered(lambda x: x.main_payment_id and x.can_edit_wizard):
            bundle_journal_id = pay.company_id._get_bundle_journal(pay.payment_type)
            pay.available_journal_ids = pay.available_journal_ids.filtered(
                lambda x: x._origin.id != bundle_journal_id
            )

    @api.depends('is_main_payment')
    def _compute_amount(self):
        """ The amount of main payment always is zero"""
        main_payments =  self.filtered('is_main_payment')
        main_payments.amount = 0
        super(AccountPaymentRegister, self - main_payments)._compute_amount()

    def _get_total_amounts_to_pay(self, batch_results):
        res = super()._get_total_amounts_to_pay(batch_results)
        if self.main_payment_id:
            payment_total = self.main_payment_id.currency_id._convert(
                    self.main_payment_id.payment_total,
                    self.currency_id,
                    self.company_id,
                    self.payment_date,
            )
            res['amount_by_default'] = res['amount_by_default'] - abs(payment_total)
        return res

    def action_create_payments(self):
        action = super().action_create_payments()
        for rec in self.link_payment_ids:
            super(AccountPaymentRegister, rec).with_context(default_main_payment_id=self.new_main_payment_id.id).action_create_payments()
        return action

    def _create_payments(self):
        payments = super()._create_payments()
        if self.is_main_payment:
            self.new_main_payment_id = payments.id
        return payments

    @api.depends("link_payment_ids", "payment_date", 'currency_id')
    def _compute_payment_total(self):
        """
            The payment_total is the sum links payment amount in currency
        """
        for wizard in self:
            wizard.payment_total = 0
            for rec in wizard.link_payment_ids:
                wizard.payment_total += rec.currency_id._convert(
                    rec.amount,
                    wizard.currency_id,
                    wizard.company_id,
                    wizard.payment_date
                )

    @api.depends('payment_total')
    def _compute_payment_difference(self):
        """ The amount of main payment always is zero
            The payment difference of the main payment is the computed difference minus
            the total of the linked payments (payment_total)
            linked payments not have payment difference.
        """
        super()._compute_payment_difference()
        for wizard in self.filtered('is_main_payment'):
            if wizard.payment_date and wizard.payment_difference:
                wizard.payment_difference -= abs(wizard.payment_total)
        self.filtered('main_payment_id').payment_difference = 0
