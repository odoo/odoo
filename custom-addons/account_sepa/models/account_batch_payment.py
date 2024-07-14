# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, float_repr, DEFAULT_SERVER_DATE_FORMAT

import base64
import re
from datetime import datetime


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    sct_batch_booking = fields.Boolean(string="SCT Batch Booking", default=True, help="Request batch booking from the bank for the related bank statements.")
    sct_generic = fields.Boolean(compute='_compute_sct_generic',
        help=u"Technical feature used during the file creation. A SEPA message is said to be 'generic' if it cannot be considered as "
             u"a standard european credit transfer. That is if the bank journal is not in €, a transaction is not in € or a payee is "
             u"not identified by an IBAN account number.")

    @api.depends('payment_ids', 'journal_id')
    def _compute_sct_generic(self):
        switch_to_generic_warnings = {'no_iban', 'no_eur'}
        for record in self:
            sct_warnings = record._get_sct_genericity_warnings()
            record.sct_generic = any(warning.get('code') in switch_to_generic_warnings for warning in sct_warnings) or record.journal_id.sepa_pain_version == 'iso_20022'

    def _get_methods_generating_files(self):
        rslt = super(AccountBatchPayment, self)._get_methods_generating_files()
        rslt.append('sepa_ct')
        return rslt

    def validate_batch(self):
        for batch in self.filtered(lambda x: x.payment_method_code == 'sepa_ct'):
            if batch.journal_id.bank_account_id.acc_type != 'iban':
                raise UserError(_("The account %s, of journal '%s', is not of type IBAN.\nA valid IBAN account is required to use SEPA features.", batch.journal_id.bank_account_id.acc_number, batch.journal_id.name))

        return super(AccountBatchPayment, self).validate_batch()

    def _get_sct_genericity_warnings(self):
        self.ensure_one()

        if self.journal_id.sepa_pain_version == 'iso_20022':
            # Forcing generic SEPA; so no genericity warning
            return []

        rslt = []
        no_iban_payments = self.env['account.payment']
        no_eur_payments = self.env['account.payment']
        invalid_address_payments = self.env['account.payment']
        invalid_ref_payments = self.env['account.payment']

        for payment in self.mapped('payment_ids'):
            if payment.partner_bank_id.acc_type != 'iban':
                no_iban_payments += payment
            if payment.currency_id.name != 'EUR':
                no_eur_payments += payment

        if no_iban_payments:
            rslt.append({
                'code': 'no_iban',
                'title': _("Some payments are not made on an IBAN recipient account. This batch might not be accepted by certain banks because of that."),
                'records': no_iban_payments,
            })

        if no_eur_payments:
            rslt.append({
                'code': 'no_eur',
                'title': _("Some payments were instructed in another currency than Euro. This batch might not be accepted by certain banks because of that."),
                'records': no_eur_payments,
            })

        return rslt

    def check_payments_for_warnings(self):
        rslt = super(AccountBatchPayment, self).check_payments_for_warnings()

        if self.payment_method_code == 'sepa_ct':
            sct_warnings = self._get_sct_genericity_warnings()
            if (self.journal_id.currency_id or self.journal_id.company_id.currency_id).name != 'EUR':
                sct_warnings = [warning for warning in sct_warnings if warning.get('code') != 'no_eur']
            rslt += sct_warnings

        return rslt

    def check_payments_for_errors(self):
        rslt = super(AccountBatchPayment, self).check_payments_for_errors()

        if self.payment_method_code != 'sepa_ct':
            return rslt

        no_bank_acc_payments = self.env['account.payment']
        too_big_payments = self.env['account.payment']

        for payment in self.payment_ids.filtered(lambda x: x.state == 'posted'):
            if not payment.partner_bank_id:
                no_bank_acc_payments += payment

            max_digits = payment.currency_id.name == 'EUR' and 11 or 15
            if len(float_repr(payment.amount, 2)) >= max_digits: # The dot counts in this limit
                too_big_payments += payment

        if no_bank_acc_payments:
            rslt.append({'title': _("Some payments have no recipient bank account set."), 'records': no_bank_acc_payments})

        if too_big_payments:
            rslt.append({
                'title': _("Some payments are above the maximum amount allowed."),
                'records': too_big_payments,
                'help': _("Maximum amount is %s for payments in Euros, %s for other currencies.", 8 * '9' + ".99", 12 * '9' + ".99")
            })

        return rslt

    def _generate_export_file(self):
        if self.payment_method_code == 'sepa_ct':
            payments = self.payment_ids.sorted(key=lambda r: r.id)
            payment_dicts = self._generate_payment_template(payments)
            xml_doc = self.journal_id.create_iso20022_credit_transfer(payment_dicts, self.sct_batch_booking, self.sct_generic)
            return {
                'file': base64.encodebytes(xml_doc),
                'filename': "SCT-" + self.journal_id.code + "-" + datetime.now().strftime('%Y%m%d%H%M%S') + ".xml",
            }

        return super(AccountBatchPayment, self)._generate_export_file()

    def _get_payment_vals(self, payment):

        return {
            'id' : payment.id,
            'name': str(payment.id) + '-' + (payment.ref or 'SCT-' + self.journal_id.code + '-' + str(fields.Date.today())),
            'payment_date' : payment.date,
            'amount' : payment.amount,
            'journal_id' : self.journal_id.id,
            'currency_id' : payment.currency_id.id,
            'payment_type' : payment.payment_type,
            'ref' : payment.ref,
            'partner_id' : payment.partner_id.id,
            'partner_bank_id': payment.partner_bank_id.id,
            'partner_country_code': payment.partner_id.country_id.code,
            'sepa_uetr': payment.sepa_uetr,
        }

    def _generate_payment_template(self, payments):
        payment_dicts = []
        for payment in payments:
            if not payment.partner_bank_id:
                raise UserError(_('A bank account is not defined.'))

            payment_dicts.append(self._get_payment_vals(payment))

        return payment_dicts
