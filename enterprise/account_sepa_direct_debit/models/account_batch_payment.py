# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import base64
import re
from datetime import datetime, timedelta

from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, ValidationError, UserError
from odoo.tools import SQL, format_date

from odoo.addons.account_sepa_direct_debit.models.sdd_mandate import SDD_MIN_PRENOT_PERIOD, SDD_FIRST_MIN_PRENOT_PERIOD


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    sdd_required_collection_date = fields.Date(
        string='Required Collection Date',
        compute='_compute_sdd_required_collection_date', store=True,
        help="Date when the company expects to receive the payments of this batch. "
             "It can't be inferior to the sending day + the minimum pre-notification period.",
    )
    sdd_min_required_collection_date = fields.Date(compute='_compute_sdd_min_required_collection_date', export_string_translation=False)
    sdd_first_time_payment_ids = fields.One2many('account.payment', compute='_compute_sdd_first_time_payment_ids', export_string_translation=False)
    sdd_batch_booking = fields.Boolean(string="SDD Batch Booking", default=True, help="Request batch booking from the bank for the related bank statements.")
    sdd_scheme = fields.Selection(string="SDD Scheme", selection=[('CORE', 'CORE'), ('B2B', 'B2B')],
    help='The B2B scheme is an optional scheme,\noffered exclusively to business payers.\nSome banks/businesses might not accept B2B SDD.',
    compute='_compute_sdd_scheme', store=True, readonly=False)

    @api.depends('sdd_scheme')
    def _compute_payment_ids_domain(self):
        super()._compute_payment_ids_domain()
        for batch in self:
            domain = ast.literal_eval(batch.payment_ids_domain)
            domain.extend([
                '|',
                    ('payment_method_id.code', 'not in', ('sdd', 'sepa_direct_debit')),
                    ('sdd_mandate_id.sdd_scheme', '=', batch.sdd_scheme),
            ])
            batch.payment_ids_domain = str(domain)

    @api.depends('payment_ids')
    def _compute_sdd_required_collection_date(self):
        """
        The regulation requires that the payer's bank must receive the request for a first direct debit collection
        the latest 5 business days prior to the due date. For subsequent direct debit collections,
        the payer's bank must receive such a request the latest 2 business days prior to the due date.
        """
        sepa_codes = set(self.env['account.payment.method']._get_sdd_payment_method_code())
        for batch in self.filtered(lambda batch: batch.payment_method_code in sepa_codes):
            if batch.sdd_required_collection_date:  # Do not override when there is a time
                batch.sdd_required_collection_date = batch.sdd_required_collection_date
                continue

            minimum_offset = SDD_FIRST_MIN_PRENOT_PERIOD
            mandates = batch.payment_ids.sdd_mandate_id
            all_used_mandates = batch._get_all_used_mandates()
            if all(all_used_mandates.get(mandate, 0) > 0 for mandate in mandates):
                # The minimum delay is 5 days in all cases, except when all the mandates involved were already used once
                # before, then it can be 2 days.
                minimum_offset = SDD_MIN_PRENOT_PERIOD

            batch.sdd_required_collection_date = fields.Date.context_today(batch) + timedelta(
                max([minimum_offset, *mandates.mapped('pre_notification_period')])
            )

    @api.depends('payment_ids')
    def _compute_sdd_min_required_collection_date(self):
        """Compute the minimum required collection date according to SEPA if there are unused mandates."""
        sepa_codes = set(self.env['account.payment.method']._get_sdd_payment_method_code())
        for batch in self:
            if batch.payment_method_code not in sepa_codes:
                batch.sdd_min_required_collection_date = False
                continue

            mandates = batch.payment_ids.sdd_mandate_id
            all_used_mandates = batch._get_all_used_mandates()
            if all(all_used_mandates.get(mandate, 0) > 0 for mandate in mandates):
                # The minimum delay is 5 days in all cases, except when all the mandates involved were already used once
                # before, then it can be 2 days.
                batch.sdd_min_required_collection_date = False
            else:
                batch.sdd_min_required_collection_date = fields.Date.context_today(batch) + timedelta(
                    SDD_FIRST_MIN_PRENOT_PERIOD
                )

    @api.depends('payment_ids')
    def _compute_sdd_first_time_payment_ids(self):
        """Compute the payments in the batch having mandates that were never used before."""
        sepa_codes = set(self.env['account.payment.method']._get_sdd_payment_method_code())
        for batch in self:
            if batch.payment_method_code not in sepa_codes:
                batch.sdd_first_time_payment_ids = False
                continue

            all_used_mandates = batch._get_all_used_mandates()
            batch.sdd_first_time_payment_ids = batch.payment_ids.filtered(
                lambda p: all_used_mandates.get(p.sdd_mandate_id, 0) == 0
            )

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

    def _get_all_used_mandates(self):
        """Retrieve a dict, mapping all used mandates in this batch payment to the number of uses.

        :return: Used mandates mapped to the number of uses.
        :rtype: dict[:class:`odoo.addons.account_sepa_direct_debit.models.SDDMandate`, int]
        """
        self.ensure_one()
        mandates = self.payment_ids.sdd_mandate_id
        return dict(self.env['account.payment']._read_group([
            ('sdd_mandate_id', 'in', mandates.ids),
            ('is_matched', '=', True),
            ],
            groupby=['sdd_mandate_id'],
            aggregates=['__count'],
        ))

    def _get_methods_generating_files(self):
        rslt = super()._get_methods_generating_files()
        rslt += self.payment_method_id._get_sdd_payment_method_code()
        return rslt

    @api.constrains('sdd_required_collection_date', 'payment_method_id')
    def _check_minimal_collection_date(self):
        sepa_codes = self.env['account.payment.method']._get_sdd_payment_method_code()

        sepa_batch_payment = self.filtered(lambda p: p.payment_method_code in sepa_codes)
        if not sepa_batch_payment:
            return

        for batch in sepa_batch_payment:
            minimum_date = fields.Date.context_today(batch) + timedelta(days=SDD_MIN_PRENOT_PERIOD)
            if batch.payment_method_code in sepa_codes and batch.sdd_required_collection_date < minimum_date:
                raise ValidationError(_(
                    "The bank needs to be informed at least %(min_days_new)s days in advance for collections related "
                    "to a new mandate and %(min_days)s days in advance when the mandate is already known by them.\n"
                    "The minimum collection date must be %(date)s.",
                    min_days_new=SDD_FIRST_MIN_PRENOT_PERIOD,
                    min_days=SDD_MIN_PRENOT_PERIOD,
                    date=format_date(self.env, minimum_date),
                ))

    @api.constrains('batch_type', 'journal_id', 'payment_ids', 'payment_method_id')
    def _check_payments_constrains(self):
        super(AccountBatchPayment, self)._check_payments_constrains()
        for record in self.filtered(lambda r: r.payment_method_code in r.payment_method_id._get_sdd_payment_method_code()):
            all_sdd_schemes = set(record.payment_ids.mapped('sdd_mandate_id.sdd_scheme'))
            if len(all_sdd_schemes) > 1:
                raise ValidationError(_("All the payments in the batch must have the same SDD scheme."))

    def validate_batch(self):
        self.ensure_one()
        if self.payment_method_code in self.payment_method_id._get_sdd_payment_method_code():
            today = fields.Date.context_today(self)
            company = self.journal_id.company_id

            if not company.sdd_creditor_identifier:
                action = self.env.ref('account.action_account_config')
                raise RedirectWarning(_(
                    "Your company must have a creditor identifier in order to issue SEPA Direct Debit payments requests. "
                    "It can be defined in accounting module's settings."
                    ),
                    action=action.id,
                    button_text=_("Go to settings"),
                )

            payments_without_mandate = self.payment_ids.filtered(lambda x: not x.sdd_mandate_id)
            if payments_without_mandate:
                raise RedirectWarning(
                    _("Some payments are not linked to any mandate."),
                    action={
                        'name': _("Payments without mandate"),
                        'type': 'ir.actions.act_window',
                        'res_model': 'account.payment',
                        'views': [(self.env.ref('account.view_account_payment_tree').id, 'list')],
                        'domain': [('id', 'in', payments_without_mandate.ids)]
                    },
                    button_text=_("Go to payments"),
                )

            invalid_mandates = self.payment_ids.sdd_mandate_id._update_and_partition_state_by_validity()['invalid']
            if invalid_mandates:
                raise RedirectWarning(
                    _("Some payments are linked to an inactive mandate."),
                    action={
                        'name': _("Problematic mandates"),
                        'type': 'ir.actions.act_window',
                        'res_model': 'sdd.mandate',
                        'views': [(self.env.ref('account_sepa_direct_debit.account_sepa_direct_debit_mandate_tree').id, 'list')],
                        'domain': [('id', 'in', invalid_mandates.ids)],
                    },
                    button_text=_("Go to mandates"),
                )

            # Check that the pre-notification delay is good
            collection_date = self.sdd_required_collection_date
            min_collection_date = today + timedelta(days=SDD_MIN_PRENOT_PERIOD)
            if collection_date < min_collection_date:
                raise UserError(_(
                    "You cannot generate a SEPA Direct Debit file with a required collection date inferior to the "
                    "sending day + the minimum pre-notification period of %(prenot_days)s days.\n"
                    "The minimum required date should be %(minimum_date)s.",
                    prenot_days=SDD_MIN_PRENOT_PERIOD,
                    minimum_date=format_date(self.env, min_collection_date),
                ))

            if self.journal_id.bank_account_id.acc_type != 'iban':
                raise RedirectWarning(_(
                        "Only IBAN account numbers can receive SEPA Direct Debit payments. "
                        "Please select a journal associated to one or add an IBAN bank account to the current journal"
                    ),
                    action={
                        'name': self.journal_id.name,
                        'type': 'ir.actions.act_window',
                        'res_model': 'account.journal',
                        'res_id': self.journal_id.id,
                        'views': [(self.env.ref('account.view_account_journal_form').id, 'form')],
                    },
                    button_text=_("Go to journal"),
                )

        return super().validate_batch()

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

        return rslt + super()._check_and_post_draft_payments(draft_payments)

    def _generate_export_file(self):
        if self.payment_method_code in self.payment_method_id._get_sdd_payment_method_code():
            # Constrains on models ensure all the payments can generate SDD data before
            # calling this method, so we make no further check of their content here
            company = self.env.company
            return {
                'filename': 'PAIN008' + datetime.now().strftime('%Y%m%d%H%M%S') + '.xml',
                'file': base64.encodebytes(self.payment_ids.generate_xml(company, self.sdd_required_collection_date, self.sdd_batch_booking)),
            }

        return super()._generate_export_file()

    def _send_after_validation(self):
        """ Notify the customer that a debit has been made from his account.

        This is required as per the SEPA Direct Debit rulebook.
        The notice must include:
            - the last 4 digits of the debtor's bank account
            - the mandate reference
            - the amount to be debited
            - your SEPA creditor identifier
            - your contact information
        Notifications should be sent at least 14 calendar days before the payment is created unless
        specified otherwise (We changed that default in Odoo by always specifying the period and defaulting it to 2).

        :param recordset token: The token linked to the mandate from which the debit has been made,
                                as a `payment.token` record
        :return: None
        """
        res = super()._send_after_validation()
        if self.env['ir.config_parameter'].sudo().get_param('account_sepa_direct_debit.disable_sdd_pre_notification'):
            return res

        template = self.env.ref('account_sepa_direct_debit.email_template_sdd_pre_notification')
        sdd_codes = set(self.env['account.payment.method']._get_sdd_payment_method_code())
        for payment in self.payment_ids.filtered(lambda payment: payment.payment_method_code in sdd_codes and payment.sdd_mandate_id):
            mandate = payment.sdd_mandate_id
            sanitized_acc_number = mandate.partner_bank_id.sanitized_acc_number
            anonymized_bank_account_number = f"{re.sub(r'.', '*', sanitized_acc_number[:-4])}{sanitized_acc_number[-4:]}"

            ctx = {
                'iban_last_4': sanitized_acc_number[-4:],
                'mandate_ref': mandate.name,
                'collection_date': payment.batch_payment_id.sdd_required_collection_date,
                'amount': payment.amount,
                'creditor_iban': anonymized_bank_account_number,
            }
            payment.with_context(ctx).message_post_with_source(source_ref=template, subtype_xmlid='mail.mt_note')
        return res

    def check_payments_for_errors(self):
        rslt = super().check_payments_for_errors()

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
