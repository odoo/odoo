# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re

from datetime import date, datetime

from odoo import models, fields, api, _

from odoo.exceptions import ValidationError, UserError

class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    sdd_required_collection_date = fields.Date(string='Required collection date', default=fields.Date.today, help="Date when the company expects to receive the payments of this batch.")
    sdd_batch_booking = fields.Boolean(string="SDD Batch Booking", default=True, help="Request batch booking from the bank for the related bank statements.")
    sdd_scheme = fields.Selection(string="SDD Scheme", selection=[('CORE', 'CORE'), ('B2B', 'B2B')],
    help='The B2B scheme is an optional scheme,\noffered exclusively to business payers.\nSome banks/businesses might not accept B2B SDD.',
    compute='_compute_sdd_scheme', store=True, readonly=False)

    @api.depends('payment_method_id')
    def _compute_sdd_scheme(self):
        sdd_payment_codes = self.payment_method_id._get_sdd_payment_method_code()
        for batch in self:
            if batch.payment_method_id.code not in sdd_payment_codes:
                batch.sdd_scheme = False
            else:
                if batch.sdd_scheme:
                    batch.sdd_scheme = batch.sdd_scheme
                else:
                    batch.sdd_scheme = batch.payment_ids and batch.payment_ids[0].sdd_mandate_scheme or 'CORE'

    def _get_methods_generating_files(self):
        rslt = super(AccountBatchPayment, self)._get_methods_generating_files()
        rslt += self.payment_method_id._get_sdd_payment_method_code()
        return rslt
    
    @api.constrains('batch_type', 'journal_id', 'payment_ids')
    def _check_payments_constrains(self):
        super(AccountBatchPayment, self)._check_payments_constrains()
        for record in self.filtered(lambda r: r.payment_method_code in r.payment_method_id._get_sdd_payment_method_code()):
            all_sdd_schemes = set(record.payment_ids.mapped('sdd_mandate_id.sdd_scheme'))
            if len(all_sdd_schemes) > 1:
                raise ValidationError(_("All the payments in the batch must have the same SDD scheme."))

    def validate_batch(self):
        self.ensure_one()
        if self.payment_method_code in self.payment_method_id._get_sdd_payment_method_code():
            company = self.journal_id.company_id

            if not company.sdd_creditor_identifier:
                raise UserError(_("Your company must have a creditor identifier in order to issue SEPA Direct Debit payments requests. It can be defined in accounting module's settings."))

            collection_date = self.sdd_required_collection_date
            if collection_date < date.today():
                raise UserError(_("You cannot generate a SEPA Direct Debit file with a required collection date in the past."))

        return super(AccountBatchPayment, self).validate_batch()

    def _check_and_post_draft_payments(self, draft_payments):
        rslt = []
        if self.payment_method_code in self.payment_method_id._get_sdd_payment_method_code():

            drafts_without_mandate = draft_payments.filtered(lambda x: not x.get_usable_mandate())
            if drafts_without_mandate:
                rslt = [{'title': _("Some draft payments could not be posted because of the lack of any active mandate."),
                         'records': drafts_without_mandate,
                         'help': _("To solve that, you should create a mandate for each of the involved customers, valid at the moment of the payment date.")
                }]
                draft_payments -= drafts_without_mandate

        return rslt + super(AccountBatchPayment, self)._check_and_post_draft_payments(draft_payments)

    def _generate_export_file(self):
        if self.payment_method_code in self.payment_method_id._get_sdd_payment_method_code():
            # Constrains on models ensure all the payments can generate SDD data before
            # calling this method, so we make no further check of their content here

            company = self.env.company

            return {
                'filename': 'PAIN008' + datetime.now().strftime('%Y%m%d%H%M%S') + '.xml',
                'file': base64.encodebytes(self.payment_ids.generate_xml(company, self.sdd_required_collection_date, self.sdd_batch_booking)),
            }

        return super(AccountBatchPayment, self)._generate_export_file()

    def check_payments_for_errors(self):
        rslt = super(AccountBatchPayment, self).check_payments_for_errors()

        if self.payment_method_code not in self.payment_method_id._get_sdd_payment_method_code():
            return rslt

        if len(self.payment_ids):
            sdd_scheme = self.payment_ids[0].sdd_mandate_id.sdd_scheme
            dif_scheme_payements = self.payment_ids.filtered(lambda x: x.sdd_mandate_id.sdd_scheme != sdd_scheme)
            if dif_scheme_payements:
                rslt.append({
                    'title': _("All the payments in the batch must have the same SDD scheme."),
                    'records': dif_scheme_payements,
                    'help': _("SDD scheme is set on the customer mandate.")
                })

        return rslt
