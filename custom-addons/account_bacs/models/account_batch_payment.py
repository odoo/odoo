# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError

from dateutil.relativedelta import relativedelta

import base64

MAX_PAYMENT_AMOUNT = 999999999.99

class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    bacs_multi_mode = fields.Boolean(string="BACS Multi Mode", help="Payments in batch get processed on their individual date.",)
    bacs_processing_date = fields.Date(string="BACS Processing Date", default=fields.Date.today(), help="The processing day of the BACS transaction.")
    bacs_expiry_date = fields.Date(string="BACS Expiry Date", help="The date on which the file will expire.")
    bacs_submission_serial = fields.Char(string="BACS Submission Serial", store=True, default=lambda self: self._default_bacs_submission_serial())

    def _default_bacs_submission_serial(self):
        """
        Generate a unique 6-character BACS submission serial number based on the day of the year and the sequence number.

        This function first checks the day of the year either from the `self.date` attribute or from the current date if `self.date` is not set.
        It then fetches the last submission made on the same day from the database and increments its sequence number by one to generate a new serial.

        Returns:
        - str: A unique 6-character BACS submission serial number in the format "{day_of_year}{sequence:03d}"

        Raises:
        - UserError: If the sequence number exceeds 999 for the day.
        The 999 limit is set to ensure that the 6-character length of the BACS submission serial is not exceeded.
        """
        if self.date:
            day_of_year = self.date.strftime('%j')
        else:
            day_of_year = fields.Date.today().strftime('%j')
        sequence = 1
        last_submission = self.search(
            [
                ('payment_method_code', 'in', ['bacs_dc', 'bacs_dd']),
                ('date', '=', self.date),
                ('bacs_submission_serial', '!=', False),
                ('journal_id.company_id', '=', self.journal_id.company_id.id)
            ], limit=1, order='bacs_submission_serial desc')
        if last_submission:
            if last_submission.bacs_submission_serial:
                sequence = int(last_submission.bacs_submission_serial[3:]) + 1
        if sequence > 999:
            raise UserError(_("The maximum number of BACS submissions (999) for the day has been reached."))
        return f"{day_of_year}{sequence:03d}"

    def _get_methods_generating_files(self):
        rslt = super(AccountBatchPayment, self)._get_methods_generating_files()
        rslt.append('bacs_dc')
        rslt.append('bacs_dd')
        return rslt

    def validate_batch(self):
        for batch in self.filtered(lambda x: x.payment_method_code == 'bacs_dc' or x.payment_method_code == 'bacs_dd'):
            company = self.env.company
            if not batch.bacs_processing_date:
                batch.bacs_processing_date = fields.Date.today()
            if not batch.bacs_expiry_date:
                if batch.bacs_multi_mode:
                    max_payment_date = max(batch.payment_ids.mapped('date'))
                    batch.bacs_expiry_date = max_payment_date + relativedelta(days=90)
                else:
                    batch.bacs_expiry_date = batch.bacs_processing_date + relativedelta(days=90)
            if not company.bacs_sun:
                raise UserError(_("The company '%s' requires a SUN to generate BACS files. Please configure it first.", company.name))
            if batch.journal_id.bank_account_id.acc_type != 'iban':
                raise UserError(_("The account %s, of journal '%s', is not of type IBAN.\nA valid IBAN account is required to use BACS features.", batch.journal_id.bank_account_id.acc_number, batch.journal_id.name))
            if batch.bacs_processing_date < fields.Date.today():
                raise UserError(_("The processing date cannot be in the past."))

        return super(AccountBatchPayment, self).validate_batch()

    def check_payments_for_errors(self):
        rslt = super(AccountBatchPayment, self).check_payments_for_errors()

        if self.payment_method_code not in ['bacs_dc', 'bacs_dd']:
            return rslt

        no_bank_acc_payments = self.env['account.payment']
        too_big_payments = self.env['account.payment']
        currency_not_gbp_payments = self.env['account.payment']
        gbp_currency_id = self.env.ref('base.GBP')

        for payment in self.payment_ids.filtered(lambda x: x.state == 'posted'):
            if not payment.partner_bank_id and payment.payment_method_code == 'bacs_dc':
                no_bank_acc_payments += payment

            if payment.amount > MAX_PAYMENT_AMOUNT:
                too_big_payments += payment

            if payment.currency_id != gbp_currency_id:
                currency_not_gbp_payments += payment

        if no_bank_acc_payments:
            rslt.append({'title': _("Some payments have no recipient bank account set."), 'records': no_bank_acc_payments})

        if too_big_payments:
            rslt.append({
                'title': _("Some payments are above the maximum amount allowed."),
                'records': too_big_payments,
                'help': _("Maximum amount is %.2f.", MAX_PAYMENT_AMOUNT)
            })

        if currency_not_gbp_payments:
            rslt.append({'title': _("Some payments are not in GBP."), 'records': currency_not_gbp_payments})

        return rslt

    def _generate_export_file(self):
        self.ensure_one()
        if self.payment_method_code not in ['bacs_dc', 'bacs_dd']:
            return super(AccountBatchPayment, self)._generate_export_file()
        payments = self.payment_ids.sorted(key=lambda r: r.date)
        if self.payment_method_code == 'bacs_dd':
            payment_template = self._generate_bacs_dd_payment_template(payments)
        else:
            payment_template = self._generate_bacs_dc_payment_template(payments)
        bacs_file = self.journal_id.create_bacs_file(payment_template, self.payment_method_code, self.bacs_submission_serial, self.bacs_multi_mode, self.bacs_processing_date, self.bacs_expiry_date, self.name, self.date)
        return {
            'file': base64.encodebytes(bacs_file.encode()),
            'filename': f"{self.payment_method_code}_{self.bacs_submission_serial}.txt"
        }

    def _generate_bacs_dd_payment_template(self, payments):
        payment_dicts = []
        for payment in payments:
            payment_dict = {
                'id' : payment.id,
                'payment_date' : payment.date,
                'amount' : payment.amount,
                'journal_id' : self.journal_id.id,
                'payment_type' : payment.payment_type,
                'ref' : payment.name,
                'partner_name' : payment.partner_id.name,
                'bacs_ddi_id': payment.bacs_ddi_id.id,
                'bacs_payment_type': payment.bacs_payment_type,
            }

            payment_dicts.append(payment_dict)

        return payment_dicts

    def _generate_bacs_dc_payment_template(self, payments):
        payment_dicts = []
        for payment in payments:
            if not payment.partner_bank_id:
                raise UserError(_('A bank account is not defined.'))

            payment_dict = {
                'id' : payment.id,
                'payment_date' : payment.date,
                'amount' : payment.amount,
                'journal_id' : self.journal_id.id,
                'payment_type' : payment.payment_type,
                'ref' : payment.name,
                'partner_name' : payment.partner_id.name,
                'partner_bank_iban': payment.partner_bank_id.sanitized_acc_number,
            }

            payment_dicts.append(payment_dict)

        return payment_dicts

    @api.onchange('date')
    def _compute_bacs_submission_serial(self):
        """ Generate a new submission serial number based on the last one
            This serial number is composed of the day of the year (3 digits)
            and the sequence number of the submission for this day (3 digits).
            The sequence number is reset to 0 each day.
            This is put in place to make sure submisions are unique for each day of the year.
        """
        if self.payment_method_code not in ['bacs_dc', 'bacs_dd']:
            return
        self.bacs_submission_serial = self._default_bacs_submission_serial()
