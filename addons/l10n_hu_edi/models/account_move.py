# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
import base64
import logging
import re

from lxml import etree
from psycopg2.errors import LockNotAvailable

from odoo import fields, models, api, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools import formatLang, float_compare, float_is_zero, float_round, float_repr, cleanup_xml_node, groupby
from odoo.tools.misc import split_every
from odoo.addons.base_iban.models.res_partner_bank import normalize_iban
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import format_bool, L10nHuEdiConnection, L10nHuEdiConnectionError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_hu_payment_mode = fields.Selection(
        [
            ("TRANSFER", "Transfer"),
            ("CASH", "Cash"),
            ("CARD", "Credit/debit card"),
            ("VOUCHER", "Voucher"),
            ("OTHER", "Other"),
        ],
        string="Payment mode",
        help="NAV expected payment mode of the invoice.",
    )

    # === EDI Fields === #
    l10n_hu_edi_state = fields.Selection(
        ######################################################################################################################
        # STATE DIAGRAM
        # * False, rejected, cancelled --[upload]--> False, sent, send_timeout
        # * sent --[query_status]--> sent, confirmed, confirmed_warning, rejected
        # * confirmed, confirmed_warning --[request_cancel]--> cancel_sent, cancel_timeout
        # * cancel_sent, cancel_pending --[query_status]--> confirmed_warning, cancel_pending, cancelled
        # * send_timeout --[recover_timeout]--> False, send_timeout, confirmed, confirmed_warning, rejected,
        # * cancel_timeout --[recover_timeout]--> confirmed_warning, cancel_sent, cancel_timeout, cancel_pending, cancelled
        ######################################################################################################################
        selection=[
            ('sent', 'Sent, waiting for response'),
            ('send_timeout', 'Timeout when sending'),
            ('confirmed', 'Confirmed'),
            ('confirmed_warning', 'Confirmed with warnings'),
            ('rejected', 'Rejected'),
            ('cancel_sent', 'Cancellation request sent'),
            ('cancel_timeout', 'Timeout when requesting cancellation'),
            ('cancel_pending', 'Cancellation request pending'),
            ('cancelled', 'Cancelled'),
        ],
        string='NAV 3.0 status',
        copy=False,
        index='btree_not_null',
    )
    l10n_hu_edi_batch_upload_index = fields.Integer(
        string='Index of invoice within a batch upload',
        copy=False,
    )
    l10n_hu_edi_attachment = fields.Binary(
        string='Invoice XML file',
        attachment=True,
        copy=False,
    )
    l10n_hu_edi_send_time = fields.Datetime(
        string='Invoice upload time',
        copy=False,
    )
    l10n_hu_edi_transaction_code = fields.Char(
        string='Transaction Code',
        index='trigram',
        copy=False,
        tracking=True,
    )

    # A dict with the following structure:
    # {
    #     'error_title': the main heading of the message
    #     'errors': a list of message items
    #     'blocking_level': {'error' | 'warning' | None}
    #         directs which blocking behaviour to adopt in the Send and Print:
    #         * error: blocks PDF generation and sending by e-mail
    #         * warning: PDF is generated and sent by e-mail, but a warning appears in the banner
    #         * None: PDF is generated and sent by e-mail, no warning appears
    # }
    l10n_hu_edi_messages = fields.Json(
        string='Transaction messages (JSON)',
        copy=False,
    )

    l10n_hu_invoice_chain_index = fields.Integer(
        string='Invoice Chain Index',
        help="""
            Index in the chain of modification invoices:
                -1 for a base invoice;
                1, 2, 3, ... for modification invoices;
                0 for rejected/cancelled invoices or if it has not yet been set.
            """,
        copy=False,
    )
    l10n_hu_edi_attachment_filename = fields.Char(
        string='Invoice XML filename',
        compute='_compute_l10n_hu_edi_attachment_filename',
    )
    l10n_hu_edi_message_html = fields.Html(
        string='Transaction messages',
        compute='_compute_message_html',
    )

    # === Constraints === #

    @api.constrains('l10n_hu_edi_state', 'state')
    def _check_posted_if_active(self):
        """ Enforce the constraint that you cannot reset to draft / cancel a posted invoice if it was already sent to NAV. """
        for move in self:
            if move.state in ['draft', 'cancel'] and move.l10n_hu_edi_state not in [False, 'rejected', 'cancelled']:
                raise ValidationError(_('Cannot reset to draft or cancel invoice %s because an electronic document was already sent to NAV!', move.name))

    # === Computes === #
    @api.depends('delivery_date')
    def _compute_invoice_currency_rate(self):
        # In Hungary, the currency rate should be based on the delivery date.
        super()._compute_invoice_currency_rate()

    @api.depends('delivery_date')
    def _compute_expected_currency_rate(self):
        super()._compute_expected_currency_rate()

    def _get_invoice_currency_rate_date(self):
        self.ensure_one()
        if self.country_code == 'HU' and self.delivery_date:
            return self.delivery_date
        return super()._get_invoice_currency_rate_date()

    @api.depends('l10n_hu_edi_messages')
    def _compute_message_html(self):
        for move in self:
            if move.l10n_hu_edi_messages:
                move.l10n_hu_edi_message_html = self.env['account.move.send']._format_error_html(move.l10n_hu_edi_messages)
            else:
                move.l10n_hu_edi_message_html = False

    @api.depends('l10n_hu_edi_state', 'state')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda m: m.l10n_hu_edi_state not in [False, 'rejected', 'cancelled']).show_reset_to_draft_button = False

    @api.depends('l10n_hu_edi_state')
    def _compute_need_cancel_request(self):
        # EXTEND 'account' to add dependencies
        return super()._compute_need_cancel_request()

    @api.depends('name')
    def _compute_l10n_hu_edi_attachment_filename(self):
        for move in self:
            move.l10n_hu_edi_attachment_filename = f'{move.name.replace("/", "_")}.xml' if move.name else 'nav30.xml'

    # === Overrides === #

    def _need_cancel_request(self):
        # EXTEND account
        # Technical annulment should be available only in debug mode
        return super()._need_cancel_request() or (self.l10n_hu_edi_state in ['confirmed', 'confirmed_warning'] and request and request.session.debug)

    def button_request_cancel(self):
        # EXTEND 'account'
        if self._need_cancel_request() and self.l10n_hu_edi_state in ['confirmed', 'confirmed_warning']:
            return {
                "name": _("Technical Annulment"),
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "l10n_hu_edi.cancellation",
                "target": "new",
                "context": {"default_invoice_id": self.id},
            }

        return super().button_request_cancel()

    # === Actions === #

    def l10n_hu_edi_button_update_status(self, from_cron=False):
        """ Attempt to update the status of the invoices in `self` """
        invoices_to_query = self.filtered(lambda m: 'query_status' in m._l10n_hu_edi_get_valid_actions())

        with L10nHuEdiConnection(self.env) as connection:
            # Call `query_status` on the invoices.
            invoices_to_query._l10n_hu_edi_query_status(connection)

            # Attempt to recover missing transactions, if any invoice is missing a transaction code
            # or has a duplicate error.
            recover_transactions_error = False
            if any(
                not m.l10n_hu_edi_transaction_code
                or any(
                    'INVOICE_NUMBER_NOT_UNIQUE' in error or 'ANNULMENT_IN_PROGRESS' in error
                    for error in m.l10n_hu_edi_messages['errors']
                )
                for m in self
            ):
                recover_transactions_error = self.company_id._l10n_hu_edi_recover_transactions(connection)

        # Error handling.
        for invoice in invoices_to_query:
            # Log invoice status in chatter.
            formatted_message = self.env['account.move.send']._format_error_html(invoice.l10n_hu_edi_messages)
            invoice.with_context(no_new_invoice=True).message_post(body=formatted_message)

        if self.env['account.move.send']._can_commit():
            self.env.cr.commit()

        # If blocking errors, raise UserError, or log if we are in a cron.
        for invoice in invoices_to_query:
            if invoice.l10n_hu_edi_messages.get('blocking_level') == 'error' or recover_transactions_error:
                if invoice.l10n_hu_edi_messages.get('blocking_level') == 'error':
                    error_text = self.env['account.move.send']._format_error_text(invoice.l10n_hu_edi_messages)
                else:
                    error_text = self.env['account.move.send']._format_error_text(recover_transactions_error)
                if not from_cron:
                    raise UserError(error_text)
                else:
                    _logger.error(error_text)

    def l10n_hu_edi_button_hide_banner(self):
        messages = self.l10n_hu_edi_messages
        if messages:
            messages['hide_banner'] = True
            self.l10n_hu_edi_messages = messages

    # === Helpers === #

    def _l10n_hu_edi_get_valid_actions(self):
        """ If any NAV 3.0 flows are applicable to the given invoice, return them, else None. """
        self.ensure_one()
        valid_actions = []
        if (
            self.country_code == 'HU'
            and self.is_sale_document()
            and self.state == 'posted'
        ):
            if self.l10n_hu_edi_state in [False, 'rejected', 'cancelled']:
                valid_actions.append('upload')
            if self.l10n_hu_edi_transaction_code:
                valid_actions.append('query_status')
            if self.l10n_hu_edi_state in ['confirmed', 'confirmed_warning']:
                valid_actions.append('request_cancel')
            if not valid_actions:
                # Placeholder to denote that the invoice was already processed with a NAV flow
                valid_actions.append(True)
        return valid_actions

    def _l10n_hu_get_chain_base(self):
        """ Get the base invoice of the invoice chain. """
        modification_invoices = self
        base_invoices = self.env['account.move']
        while modification_invoices:
            base_invoices |= modification_invoices.filtered(lambda m: not m.reversed_entry_id and not m.debit_origin_id)
            modification_invoices = modification_invoices.reversed_entry_id | modification_invoices.debit_origin_id
        return base_invoices

    def _l10n_hu_get_chain_invoices(self):
        """ Given base invoices, get all invoices in the chain. """
        chain_invoices = self
        next_invoices = self
        while (next_invoices := next_invoices.reversal_move_ids | next_invoices.debit_note_ids):
            chain_invoices |= next_invoices
        return chain_invoices

    def _l10n_hu_get_currency_rate(self):
        """ Get the invoice currency / HUF rate.

            We don't use `invoice_currency_rate` to avoid rounding error as 1/0.002470 ≃ 404.87,
            and we want exactly 404.87, i.e. the rate given by the MNB of Hungary, to avoid NAV error
            upon XML submission.
        """
        self.ensure_one()
        return self.env['res.currency']._get_conversion_rate(
            from_currency=self.currency_id,
            to_currency=self.env.ref('base.HUF'),
            company=self.company_id,
            date=self.invoice_date,
        )

    def _l10n_hu_edi_set_chain_index(self):
        """ Set the l10n_hu_invoice_chain_index field. """
        self.ensure_one()
        base_invoice = self._l10n_hu_get_chain_base()
        if base_invoice == self:
            self.l10n_hu_invoice_chain_index = -1  # -1 indicates a base invoice (0 indicates the chain index was not set).
        else:
            # Lock base invoice to prevent concurrent updates, ensuring sequence integrity.
            base_invoice._l10n_hu_edi_acquire_lock()

            chain_indexes_already_sent = base_invoice._l10n_hu_get_chain_invoices().filtered(
                lambda m: m.l10n_hu_edi_state not in ['rejected', 'cancelled']
            ).mapped('l10n_hu_invoice_chain_index')
            for i in range(1, len(chain_indexes_already_sent) + 1):
                if i not in chain_indexes_already_sent:
                    self.l10n_hu_invoice_chain_index = i
                    break

    def _l10n_hu_edi_acquire_lock(self):
        """ Acquire a write lock on the invoices in self. """
        if not self:
            return
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute('SELECT * FROM account_move WHERE id = ANY(%s) FOR UPDATE NOWAIT', [self.ids])
        except LockNotAvailable:
            raise UserError(_('Could not acquire lock on invoices - is another user performing operations on them?')) from None

    # === EDI: Flow === #

    def _l10n_hu_edi_check_invoices(self):
        hu_vat_regex = re.compile(r'\d{8}-[1-5]-\d{2}')
        hu_bank_account_regex = re.compile(r'\d{8}-\d{8}-\d{8}|\d{8}-\d{8}|[A-Z]{2}\d{2}[0-9A-Za-z]{11,30}')

        # This contains all the advance invoices that correspond to final invoices in `self`.
        advance_invoices = self.filtered(lambda m: not m._is_downpayment()).invoice_line_ids._get_downpayment_lines().mapped('move_id')

        checks = {
            'company_vat_missing': {
                'records': self.company_id.filtered(lambda c: not c.vat),
                'message': _('Please set company VAT number!'),
                'action_text': _('View Company/ies'),
            },
            'company_vat_invalid': {
                'records': self.company_id.filtered(
                    lambda c: (
                        (c.vat and not hu_vat_regex.fullmatch(c.vat))
                        or (c.l10n_hu_group_vat and not hu_vat_regex.fullmatch(c.l10n_hu_group_vat))
                    )
                ),
                'message': _('Please enter the Hungarian VAT (and/or Group VAT) number in 12345678-1-12 format!'),
                'action_text': _('View Company/ies'),
            },
            'company_address_missing': {
                'records': self.company_id.filtered(lambda c: not c.country_id or not c.zip or not c.city or not c.street),
                'message': _('Please set company Country, Zip, City and Street!'),
                'action_text': _('View Company/ies'),
            },
            'company_not_huf': {
                'records': self.company_id.filtered(lambda c: c.currency_id.name not in ['HUF', 'EUR']),
                'message': _('Please use HUF or EUR as your company currency.'),
                'action_text': _('View Company/ies'),
            },
            'partner_bank_account_invalid': {
                'records': self.partner_bank_id.filtered(lambda p: not hu_bank_account_regex.fullmatch(p.acc_number)),
                'message': _('Please set a valid recipient bank account number!'),
                'action_text': _('View partner(s)'),
            },
            'partner_vat_missing': {
                'records': self.partner_id.commercial_partner_id.filtered(
                    lambda p: p.is_company and not p.vat
                ),
                'message': _('Please set partner Tax ID on company partners!'),
                'action_text': _('View partner(s)'),
            },
            'partner_vat_invalid': {
                'records': self.partner_id.commercial_partner_id.filtered(
                    lambda p: (
                        p.is_company and p.country_code == 'HU'
                        and (
                            (p.vat and not hu_vat_regex.fullmatch(p.vat))
                            or (p.l10n_hu_group_vat and not hu_vat_regex.fullmatch(p.l10n_hu_group_vat))
                        )
                    )
                ),
                'message': _('Please enter the Hungarian VAT (and/or Group VAT) number in 12345678-1-12 format!'),
                'action_text': _('View partner(s)'),
            },
            'partner_address_missing': {
                'records': self.partner_id.commercial_partner_id.filtered(
                    lambda p: p.is_company and (not p.country_id or not p.zip or not p.city or not p.street),
                ),
                'message': _('Please set partner Country, Zip, City and Street!'),
                'action_text': _('View partner(s)'),
            },
            'invoice_date_not_today': {
                'records': self.filtered(lambda m: m.invoice_date != fields.Date.context_today(m)),
                'message': _('Please set invoice date to today!'),
                'action_text': _('View invoice(s)'),
            },
            'invoice_chain_not_confirmed': {
                'records': self.env['account.move'].union(*[
                    move._l10n_hu_get_chain_base()._l10n_hu_get_chain_invoices().filtered(
                        lambda m: (
                            m.id < move.id
                            and m.l10n_hu_edi_state in [False, 'rejected', 'cancelled']
                            and m not in self
                        )
                    )
                    for move in self
                ]),
                'message': _('The following invoices appear to be earlier in the chain, but have not yet been sent. Please send them first.'),
                'action_text': _('View invoice(s)'),
            },
            'invoice_advance_not_paid': {
                'records': advance_invoices.filtered(
                    lambda m: (
                        m.payment_state not in ['in_payment', 'paid', 'partial']
                        or m.l10n_hu_edi_state in [False, 'rejected', 'cancelled']
                            and m not in self  # It's okay to send an advance and a final invoice together, as we sort by id before sending.
                    )
                ),
                'message': _('All advance invoices must be paid and sent to NAV before the final invoice is issued.'),
                'action_text': _('View advance invoice(s)'),
            },
            'invoice_line_not_one_vat_tax': {
                'records': self.filtered(
                    lambda m: any(
                        len(l.tax_ids.filtered(lambda t: t.l10n_hu_tax_type)) != 1
                        for l in m.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
                    )
                ),
                'message': _('Please set exactly one VAT tax on each invoice line!'),
                'action_text': _('View invoice(s)'),
            },
            'invoice_line_non_vat_taxes_misconfigured': {
                'records': self.invoice_line_ids.tax_ids.filtered(
                    lambda t: not t.l10n_hu_tax_type and (not t.price_include or not t.include_base_amount)
                ),
                'message': _("Please set any non-VAT (excise) taxes to be 'Included in Price' and 'Affects subsequent taxes'!"),
                'action_text': _('View tax(es)'),
            },
            'invoice_line_vat_taxes_misconfigured': {
                'records': self.invoice_line_ids.tax_ids.filtered(
                    lambda t: t.l10n_hu_tax_type and not t.is_base_affected
                ),
                'message': _("Please set any VAT taxes to be 'Affected by previous taxes'!"),
                'action_text': _('View tax(es)'),
            },
        }

        errors = {
            f"l10n_hu_edi_{check}": {
                'message': values['message'],
                'action_text': values['action_text'],
                'action': values['records']._get_records_action(name=values['action_text']),
            }
            for check, values in checks.items()
            if values['records']
        }

        if companies_missing_credentials := self.company_id.filtered(lambda c: not c.l10n_hu_edi_server_mode):
            errors['l10n_hu_edi_company_credentials_missing'] = {
                'message': _('Please set NAV credentials in the Accounting Settings!'),
                'action_text': _('Open Accounting Settings'),
                'action': self.env.ref('account.action_account_config').with_company(companies_missing_credentials[0])._get_action_dict(),
            }

        return errors

    def _l10n_hu_edi_upload(self, connection):
        """ Generate invoice XMLs and send to NAV. """
        invoices_sorted = self.sorted(lambda m: m.id)
        for invoice in invoices_sorted:
            # If we come from the 'cancelled' state, this means the previous XML had been confirmed
            # before it was cancelled.
            # In that case, we want to keep it as a regular invoice attachment, for future reference.
            if invoice.l10n_hu_edi_state == 'cancelled':
                self.env['ir.attachment'].search([
                    ('res_model', '=', self._name),
                    ('res_id', '=', invoice.id),
                    ('res_field', '=', 'l10n_hu_edi_attachment'),
                ]).write({
                    'res_field': False,
                    'name': f'{invoice.name.replace("/", "_")}_cancelled_{invoice.l10n_hu_edi_transaction_code}.xml',
                })

            # Set chain index
            invoice._l10n_hu_edi_set_chain_index()

            # Generate XML
            invoice.l10n_hu_edi_attachment = base64.b64encode(invoice._l10n_hu_edi_generate_xml())

            # Set name & mimetype on newly-created attachment.
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', invoice.id),
                ('res_field', '=', 'l10n_hu_edi_attachment'),
            ])
            attachment.write({
                'name': invoice.l10n_hu_edi_attachment_filename,
                'mimetype': 'application/xml',
            })

        # Batch by company, with max 100 invoices per batch.
        for __, batch_company in groupby(invoices_sorted, lambda m: m.company_id):
            for batch in split_every(100, batch_company):
                self.env['account.move'].union(*batch)._l10n_hu_edi_upload_single_batch(connection)

    def _l10n_hu_edi_get_operation_type(self):
        base_invoice = self._l10n_hu_get_chain_base()
        modification_invoices = self._l10n_hu_get_chain_invoices() - base_invoice

        all_invoices_residual_zero = all(invoice.amount_residual == 0 for invoice in modification_invoices)

        if self == base_invoice:
            return 'CREATE'
        if base_invoice.amount_residual == 0 and all_invoices_residual_zero:
            return 'STORNO'
        return 'MODIFY'

    def _l10n_hu_edi_upload_single_batch(self, connection):
        try:
            token_result = connection.do_token_exchange(self.company_id.sudo()._l10n_hu_edi_get_credentials_dict())
        except L10nHuEdiConnectionError as e:
            return self.write({
                'l10n_hu_edi_state': 'rejected',
                'l10n_hu_edi_transaction_code': False,
                'l10n_hu_edi_messages': {
                    'error_title': _('Could not authenticate with NAV. Check your credentials and try again.'),
                    'errors': e.errors,
                    'blocking_level': 'error',
                },
            })

        for i, invoice in enumerate(self, start=1):
            invoice.l10n_hu_edi_batch_upload_index = i

        invoice_operations = [
            {
                'index': invoice.l10n_hu_edi_batch_upload_index,
                'operation': invoice._l10n_hu_edi_get_operation_type(),
                'invoice_data': base64.b64decode(invoice.l10n_hu_edi_attachment),
            }
            for invoice in self
        ]

        self.write({'l10n_hu_edi_send_time': fields.Datetime.now()})

        try:
            transaction_code = connection.do_manage_invoice(
                self.company_id.sudo()._l10n_hu_edi_get_credentials_dict(),
                token_result['token'],
                invoice_operations,
            )
        except L10nHuEdiConnectionError as e:
            if e.code == 'timeout':
                return self.write({
                    'l10n_hu_edi_state': 'send_timeout',
                    'l10n_hu_edi_transaction_code': False,
                    'l10n_hu_edi_messages': {
                        'error_title': _('Invoice submission timed out. Please wait at least 6 minutes, then update the status.'),
                        'errors': e.errors,
                        'blocking_level': 'warning',
                    },
                })
            return self.write({
                'l10n_hu_edi_state': 'rejected',
                'l10n_hu_edi_transaction_code': False,
                'l10n_hu_invoice_chain_index': 0,
                'l10n_hu_edi_messages': {
                    'error_title': _('Invoice submission failed.'),
                    'errors': e.errors,
                    'blocking_level': 'error',
                },
            })

        self.write({
            'l10n_hu_edi_state': 'sent',
            'l10n_hu_edi_transaction_code': transaction_code,
            'l10n_hu_edi_messages': {
                'error_title': _('Invoice submitted, waiting for response.'),
                'errors': [],
            }
        })

    def _l10n_hu_edi_query_status(self, connection):
        """ Check the NAV invoice status. """
        # We should update all invoices with the same company and transaction code at once.
        invoices = self | self.search([
            ('company_id', 'in', self.company_id.ids),
            ('l10n_hu_edi_transaction_code', 'in', self.mapped('l10n_hu_edi_transaction_code')),
            ('l10n_hu_edi_state', 'in', ['sent', 'cancel_sent']),
        ])

        # Querying status should be grouped by company and transaction code
        for __, invoices_grouped in groupby(invoices, lambda m: (m.company_id, m.l10n_hu_edi_transaction_code)):
            self.env['account.move'].union(*invoices_grouped)._l10n_hu_edi_query_status_single_batch(connection)

    def _l10n_hu_edi_query_status_single_batch(self, connection):
        """ Check the NAV status for invoices that share the same transaction code (uploaded in a single batch). """
        try:
            results = connection.do_query_transaction_status(
                self.company_id.sudo()._l10n_hu_edi_get_credentials_dict(),
                self[0].l10n_hu_edi_transaction_code,
            )
        except L10nHuEdiConnectionError as e:
            if self.l10n_hu_edi_state == 'sent':
                return self.write({
                    'l10n_hu_edi_messages': {
                        'error_title': _('The invoice was sent to the NAV, but there was an error querying its status.'),
                        'errors': e.errors,
                        'blocking_level': 'warning',
                    },
                })
            else:
                return self.write({
                    'l10n_hu_edi_messages': {
                        'error_title': _('The annulment was sent to the NAV, but there was an error querying its status.'),
                        'errors': e.errors,
                        'blocking_level': 'warning',
                    },
                })

        for processing_result in results['processing_results']:
            invoice = self.filtered(lambda m: str(m.l10n_hu_edi_batch_upload_index) == processing_result['index'])
            if not invoice:
                _logger.error(_('Could not match NAV transaction_code %(code)s, index %(index)s to an invoice in Odoo',
                                code=self[0].l10n_hu_edi_transaction_code,
                                index=processing_result['index']))
                continue

            invoice._l10n_hu_edi_process_query_transaction_result(processing_result, results['annulment_status'])

    def _l10n_hu_edi_process_query_transaction_result(self, processing_result, annulment_status):
        def get_errors_from_processing_result(processing_result):
            return [
                f'({message["validation_result_code"]}) {message["validation_error_code"]}: {message["message"]}'
                for message in processing_result.get('business_validation_messages', []) + processing_result.get('technical_validation_messages', [])
            ]

        self.ensure_one()

        if processing_result['invoice_status'] in ['RECEIVED', 'PROCESSING', 'SAVED']:
            # The invoice/annulment has not been processed yet.
            if self.l10n_hu_edi_state in ['sent', 'send_timeout']:
                self.write({
                    'l10n_hu_edi_state': 'sent',
                    'l10n_hu_edi_messages': {
                        'error_title': _('The invoice was received by the NAV, but has not been confirmed yet.'),
                        'errors': get_errors_from_processing_result(processing_result),
                        'blocking_level': 'warning',
                    },
                })
            elif self.l10n_hu_edi_state in ['cancel_sent', 'cancel_timeout']:
                self.write({
                    'l10n_hu_edi_state': 'cancel_sent',
                    'l10n_hu_edi_messages': {
                        'error_title': _('The annulment request was received by the NAV, but has not been confirmed yet.'),
                        'errors': get_errors_from_processing_result(processing_result),
                        'blocking_level': 'warning',
                    },
                })

        elif processing_result['invoice_status'] == 'DONE':
            if self.l10n_hu_edi_state in ['sent', 'send_timeout']:
                if not processing_result['business_validation_messages'] and not processing_result['technical_validation_messages']:
                    self.write({
                        'l10n_hu_edi_state': 'confirmed',
                        'l10n_hu_edi_messages': {
                            'error_title': _('The invoice was successfully accepted by the NAV.'),
                            'errors': get_errors_from_processing_result(processing_result),
                        },
                    })
                else:
                    self.write({
                        'l10n_hu_edi_state': 'confirmed_warning',
                        'l10n_hu_edi_messages': {
                            'error_title': _(
                                'The invoice was accepted by the NAV, but warnings were reported. '
                                'To reverse, create a credit note / debit note.'
                            ),
                            'errors': get_errors_from_processing_result(processing_result),
                            'blocking_level': 'warning',
                        },
                    })
            elif self.l10n_hu_edi_state in ['cancel_sent', 'cancel_timeout', 'cancel_pending']:
                if annulment_status == 'NOT_VERIFIABLE':
                    self.write({
                        'l10n_hu_edi_state': 'confirmed_warning',
                        'l10n_hu_edi_messages': {
                            'error_title': _('The annulment request was rejected by NAV.'),
                            'errors': get_errors_from_processing_result(processing_result),
                            'blocking_level': 'error',
                        },
                    })
                elif annulment_status == 'VERIFICATION_PENDING':
                    self.write({
                        'l10n_hu_edi_state': 'cancel_pending',
                        'l10n_hu_edi_messages': {
                            'error_title': _('The annulment request is pending, please confirm it on the OnlineSzámla portal.'),
                            'errors': get_errors_from_processing_result(processing_result),
                            'blocking_level': 'warning',
                        }
                    })
                elif annulment_status == 'VERIFICATION_DONE':
                    # Annulling a base invoice will also annul all its modification invoices on NAV.
                    to_cancel = self if self.reversed_entry_id or self.debit_origin_id else self._l10n_hu_get_chain_invoices().filtered(lambda m: m.l10n_hu_edi_state)
                    to_cancel.write({
                        'l10n_hu_edi_state': 'cancelled',
                        'l10n_hu_invoice_chain_index': 0,
                        'l10n_hu_edi_messages': {
                            'error_title': _('The annulment request has been approved by the user on the OnlineSzámla portal.'),
                            'errors': get_errors_from_processing_result(processing_result),
                        }
                    })
                    to_cancel.button_cancel()
                elif annulment_status == 'VERIFICATION_REJECTED':
                    self.write({
                        'l10n_hu_edi_state': 'confirmed_warning',
                        'l10n_hu_edi_messages': {
                            'error_title': _('The annulment request was rejected by the user on the OnlineSzámla portal.'),
                            'errors': get_errors_from_processing_result(processing_result),
                            'blocking_level': 'error',
                        }
                    })

        elif processing_result['invoice_status'] == 'ABORTED':
            if self.l10n_hu_edi_state in ['sent', 'send_timeout']:
                self.write({
                    'l10n_hu_edi_state': 'rejected',
                    'l10n_hu_invoice_chain_index': 0,
                    'l10n_hu_edi_messages': {
                        'error_title': _('The invoice was rejected by the NAV.'),
                        'errors': get_errors_from_processing_result(processing_result),
                        'blocking_level': 'error',
                    },
                })
            elif self.l10n_hu_edi_state in ['cancel_sent', 'cancel_timeout', 'cancel_pending']:
                self.write({
                    'l10n_hu_edi_state': 'confirmed_warning',
                    'l10n_hu_edi_messages': {
                        'error_title': _('The cancellation request could not be performed.'),
                        'errors': get_errors_from_processing_result(processing_result),
                        'blocking_level': 'error',
                    },
                })

    def _l10n_hu_edi_request_cancel(self, connection, code, reason):
        """ Send a cancellation request for all invoices in `self`. """
        # Batch by company, with max 100 annulment requests per batch.
        for __, batch_company in groupby(self, lambda m: m.company_id):
            for batch in split_every(100, batch_company):
                self.env['account.move'].union(*batch)._l10n_hu_edi_request_cancel_single_batch(connection, code, reason)

    def _l10n_hu_edi_request_cancel_single_batch(self, connection, code, reason):
        for i, invoice in enumerate(self, start=1):
            invoice.l10n_hu_edi_batch_upload_index = i

        annulment_operations = [
            {
                'index': invoice.l10n_hu_edi_batch_upload_index,
                'annulmentReference': invoice.name,
                'annulmentCode': code,
                'annulmentReason': reason,
            }
            for invoice in self
        ]

        try:
            token_result = connection.do_token_exchange(self.company_id.sudo()._l10n_hu_edi_get_credentials_dict())
        except L10nHuEdiConnectionError as e:
            return self.write({
                'l10n_hu_edi_messages': {
                    'error_title': _('Could not authenticate with NAV. Check your credentials and try again.'),
                    'errors': e.errors,
                    'blocking_level': 'error',
                },
            })

        self.write({'l10n_hu_edi_send_time': fields.Datetime.now()})

        try:
            transaction_code = connection.do_manage_annulment(
                self.company_id.sudo()._l10n_hu_edi_get_credentials_dict(),
                token_result['token'],
                annulment_operations,
            )
        except L10nHuEdiConnectionError as e:
            if e.code == 'timeout':
                return self.write({
                    'l10n_hu_edi_state': 'cancel_timeout',
                    'l10n_hu_edi_messages': {
                        'error_title': _('Cancellation request timed out. Please wait at least 6 minutes, then update the status.'),
                        'errors': e.errors,
                        'blocking_level': 'warning',
                    },
                })
            return self.write({
                'l10n_hu_edi_messages': {
                    'error_title': _('Cancellation request failed.'),
                    'errors': e.errors,
                    'blocking_level': 'error',
                },
            })

        self.write({
            'l10n_hu_edi_state': 'cancel_sent',
            'l10n_hu_edi_transaction_code': transaction_code,
            'l10n_hu_edi_messages': {
                'error_title': _('Cancellation request submitted, waiting for response.'),
                'errors': [],
            }
        })

    # === EDI: XML generation === #

    def _l10n_hu_edi_generate_xml(self):
        invoice_data = self.env['ir.qweb']._render(
            self._l10n_hu_edi_get_electronic_invoice_template(),
            self._l10n_hu_edi_get_invoice_values(),
        )
        return etree.tostring(cleanup_xml_node(invoice_data, remove_blank_nodes=False), xml_declaration=True, encoding='UTF-8')

    def _l10n_hu_edi_get_electronic_invoice_template(self):
        """ For feature extensibility. """
        return 'l10n_hu_edi.nav_online_invoice_xml_3_0'

    def _l10n_hu_edi_get_invoice_values(self):
        eu_country_codes = set(self.env.ref('base.europe').country_ids.mapped('code'))

        def get_vat_data(partner, force_vat=None):
            if partner.country_code == 'HU' or force_vat:
                return {
                    'tax_number': partner.l10n_hu_group_vat or (force_vat or partner.vat),
                    'group_member_tax_number': partner.l10n_hu_group_vat and (force_vat or partner.vat),
                }
            elif partner.country_code in eu_country_codes:
                return {'community_vat_number': partner.vat}
            else:
                return {'third_state_tax_id': partner.vat}

        def format_bank_account_number(bank_account):
            # Normalize IBANs (no spaces!)
            if bank_account.acc_type == 'iban':
                return normalize_iban(bank_account.acc_number)
            else:
                return bank_account.acc_number

        supplier = self.company_id.partner_id
        customer = self.partner_id.commercial_partner_id

        supplier_bank = self.partner_bank_id if self.partner_bank_id and self.move_type == "out_invoice" else supplier.bank_ids[:1]
        customer_bank = self.partner_bank_id if self.partner_bank_id and self.move_type == "out_refund" else customer.bank_ids[:1]

        currency_huf = self.env.ref('base.HUF')
        currency_rate = self._l10n_hu_get_currency_rate()

        base_invoice = self._l10n_hu_get_chain_base()

        invoice_values = {
            'invoice': self,
            'invoiceIssueDate': self.invoice_date,
            'completenessIndicator': False,
            'modifyWithoutMaster': False,
            'base_invoice': base_invoice if base_invoice != self else None,
            'supplier': supplier,
            'supplier_vat_data': get_vat_data(supplier, self.fiscal_position_id.foreign_vat),
            'supplierBankAccountNumber': format_bank_account_number(supplier_bank),
            'individualExemption': self.company_id.l10n_hu_tax_regime == 'ie',
            'customer': customer,
            'customerVatStatus': (not customer.is_company and 'PRIVATE_PERSON') or (customer.country_code == 'HU' and 'DOMESTIC') or 'OTHER',
            'customer_vat_data': get_vat_data(customer) if customer.is_company else None,
            'customerBankAccountNumber': format_bank_account_number(customer_bank),
            'smallBusinessIndicator': self.company_id.l10n_hu_tax_regime == 'sb',
            'exchangeRate': currency_rate,
            'cashAccountingIndicator': self.company_id.l10n_hu_tax_regime == 'ca',
            'shipping_partner': self.partner_shipping_id,
            'sales_partner': self.user_id,
            'mergedItemIndicator': False,
            'format_bool': format_bool,
            'float_repr': float_repr,
            'lines_values': [],
        }

        sign = 1.0 if self.is_inbound() else -1.0

        prev_chain_invoices = base_invoice._l10n_hu_get_chain_invoices().filtered(
            lambda m: m.l10n_hu_invoice_chain_index and m.l10n_hu_invoice_chain_index < self.l10n_hu_invoice_chain_index
        )
        first_line_number = sum(
            len(move.line_ids.filtered(lambda l: l.display_type in ['product', 'rounding']))
            for move in prev_chain_invoices
        ) + 1

        for (line_number, line) in enumerate(
            self.line_ids.filtered(lambda l: l.display_type in ['product', 'rounding']).sorted(lambda l: l.display_type),
            start=first_line_number,
        ):
            line_values = {
                'line': line,
                'lineNumber': line_number - first_line_number + 1,
                'lineNumberReference': base_invoice != self and line_number,
                'lineExpressionIndicator': line.product_id and line.product_uom_id,
                'lineNatureIndicator': {False: 'OTHER', 'service': 'SERVICE'}.get(line.product_id.type, 'PRODUCT'),
                'lineDescription': line.name.replace('\n', ' '),
            }

            if 'is_downpayment' in line and line.is_downpayment:
                # Advance and final invoices.
                line_values['advanceIndicator'] = True

                if not self._is_downpayment():
                    # This is a final invoice that deducts one or more advance invoices.
                    # In this case, we add a reference to the *last-paid* advance invoice (NAV only allows us to report one) if one exists,
                    # otherwise we don't add anything.

                    advance_invoices = line._get_downpayment_lines().mapped('move_id').filtered(lambda m: m.state == 'posted')
                    reconciled_moves = advance_invoices._get_reconciled_amls().move_id
                    last_reconciled_payment = reconciled_moves.filtered(lambda m: m.origin_payment_id or m.statement_line_id).sorted('date', reverse=True)[:1]

                    if last_reconciled_payment:
                        line_values.update({
                            'advanceOriginalInvoice': advance_invoices.filtered(lambda m: last_reconciled_payment in m._get_reconciled_amls().move_id)[0].name,
                            'advancePaymentDate': last_reconciled_payment.date,
                            'advanceExchangeRate': last_reconciled_payment._l10n_hu_get_currency_rate(),
                        })

            if line.display_type == 'product':
                vat_tax = line.tax_ids.filtered(lambda t: t.l10n_hu_tax_type)

                if line.quantity == 0.0 or line.discount == 100.0:
                    price_unit_signed = 0.0
                else:
                    price_unit_signed = sign * line.price_subtotal / (1 - line.discount / 100) / line.quantity

                price_net_signed = self.currency_id.round(price_unit_signed * line.quantity * (1 - line.discount / 100.0))
                discount_value_signed = self.currency_id.round(price_unit_signed * line.quantity - price_net_signed)
                price_total_signed = sign * line.price_total
                vat_amount_signed = self.currency_id.round(price_total_signed - price_net_signed)

                line_values.update({
                    'vat_tax': vat_tax,
                    'vatPercentage': float_round(vat_tax.amount / 100.0, 4),
                    'quantity': line.quantity,
                    'unitPrice': price_unit_signed,
                    'unitPriceHUF': currency_huf.round(price_unit_signed * currency_rate),
                    'discountValue': discount_value_signed,
                    'discountRate': line.discount / 100.0,
                    'lineNetAmount': price_net_signed,
                    'lineNetAmountHUF': currency_huf.round(price_net_signed * currency_rate),
                    'lineVatData': not self.currency_id.is_zero(vat_amount_signed),
                    'lineVatAmount': vat_amount_signed,
                    'lineVatAmountHUF': currency_huf.round(vat_amount_signed * currency_rate),
                    'lineGrossAmountNormal': price_total_signed,
                    'lineGrossAmountNormalHUF': currency_huf.round(price_total_signed * currency_rate),
                })

            elif line.display_type == 'rounding':
                atk_tax = self.env['account.tax'].search(
                    [
                        ('type_tax_use', '=', 'sale'),
                        ('l10n_hu_tax_type', '=', 'ATK'),
                        ('company_id', '=', self.company_id.id),
                    ],
                    limit=1,
                )
                if not atk_tax:
                    raise UserError(_('Please create a sales tax with type ATK (outside the scope of the VAT Act).'))

                amount_huf = line.balance if self.company_id.currency_id == currency_huf else currency_huf.round(line.amount_currency * currency_rate)
                line_values.update({
                    'vat_tax': atk_tax,
                    'vatPercentage': float_round(atk_tax.amount / 100.0, 4),
                    'quantity': 1.0,
                    'unitPrice': -line.amount_currency,
                    'unitPriceHUF': -amount_huf,
                    'lineNetAmount': -line.amount_currency,
                    'lineNetAmountHUF': -amount_huf,
                    'lineVatData': False,
                    'lineGrossAmountNormal': -line.amount_currency,
                    'lineGrossAmountNormalHUF': -amount_huf,
                })
            line_values['lineDescription'] = line_values['lineDescription'] or line.product_id.display_name
            invoice_values['lines_values'].append(line_values)

        is_company_huf = self.company_id.currency_id == currency_huf
        tax_amounts_by_tax = {
            line.tax_line_id: {
                'vatRateVatAmount': -line.amount_currency,
                'vatRateVatAmountHUF': -line.balance if is_company_huf else currency_huf.round(-line.amount_currency * currency_rate),
            }
            for line in self.line_ids.filtered(lambda l: l.tax_line_id.l10n_hu_tax_type)
        }

        invoice_values['tax_summary'] = [
            {
                'vat_tax': vat_tax,
                'vatPercentage': float_round(vat_tax.amount / 100.0, 4),
                'vatRateNetAmount': self.currency_id.round(sum(l['lineNetAmount'] for l in lines_values_by_tax)),
                'vatRateNetAmountHUF': currency_huf.round(sum(l['lineNetAmountHUF'] for l in lines_values_by_tax)),
                'vatRateVatAmount': tax_amounts_by_tax.get(vat_tax, {}).get('vatRateVatAmount', 0.0),
                'vatRateVatAmountHUF': tax_amounts_by_tax.get(vat_tax, {}).get('vatRateVatAmountHUF', 0.0),
            }
            for vat_tax, lines_values_by_tax in groupby(invoice_values['lines_values'], lambda l: l['vat_tax'])
        ]

        total_vat = self.currency_id.round(sum(tax_vals['vatRateVatAmount'] for tax_vals in invoice_values['tax_summary']))
        total_vat_huf = currency_huf.round(sum(tax_vals['vatRateVatAmountHUF'] for tax_vals in invoice_values['tax_summary']))

        total_gross = self.amount_total_in_currency_signed
        total_gross_huf = self.amount_total_signed if is_company_huf else currency_huf.round(self.amount_total_in_currency_signed * currency_rate)

        total_net = self.currency_id.round(total_gross - total_vat)
        total_net_huf = currency_huf.round(total_gross_huf - total_vat_huf)

        invoice_values.update({
            'invoiceNetAmount': total_net,
            'invoiceNetAmountHUF': total_net_huf,
            'invoiceVatAmount': total_vat,
            'invoiceVatAmountHUF': total_vat_huf,
            'invoiceGrossAmount': total_gross,
            'invoiceGrossAmountHUF': total_gross_huf,
        })

        return invoice_values

    # === PDF generation === #

    def _get_name_invoice_report(self):
        self.ensure_one()
        return 'l10n_hu_edi.report_invoice_document' if self.country_code == 'HU' else super()._get_name_invoice_report()

    def _l10n_hu_get_invoice_totals_for_report(self):
        """ In Hungary, tax amounts should appear negative on credit notes.
            We therefore apply a post-processing to the tax totals to make them negative. """

        def invert_dict(dictionary, keys_to_invert):
            """ Replace the values of keys_to_invert by their negative. """
            dictionary.update({
                key: -value
                for key, value in dictionary.items()
                if key in keys_to_invert
            })

        self.ensure_one()
        tax_totals = self.tax_totals
        if not tax_totals:
            return tax_totals

        fields_to_reverse = (
            'base_amount_currency', 'base_amount',
            'display_base_amount_currency', 'display_base_amount',
            'tax_amount_currency', 'tax_amount',
            'total_amount_currency', 'total_amount',
            'cash_rounding_base_amount_currency', 'cash_rounding_base_amount',
        )

        if self.move_type in ('out_refund', 'in_refund'):
            invert_dict(tax_totals, fields_to_reverse)
            for subtotal in tax_totals['subtotals']:
                invert_dict(subtotal, fields_to_reverse)
                for tax_group in subtotal['tax_groups']:
                    invert_dict(tax_group, fields_to_reverse)

        currency_huf = self.env.ref('base.HUF')
        tax_totals['total_vat_amount_in_huf'] = sum(
            line.balance for line in self.line_ids.filtered(lambda l: l.tax_line_id.l10n_hu_tax_type)
        ) * (1 if self.is_purchase_document() else -1)
        tax_totals['formatted_total_vat_amount_in_huf'] = formatLang(
            self.env, tax_totals['total_vat_amount_in_huf'], currency_obj=currency_huf
        )

        return tax_totals
