# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import json
import logging
import time

import dateutil
from dateutil.relativedelta import relativedelta
from lxml import etree
from lxml.etree import ParseError
from pytz import UTC

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import split_every

_logger = logging.getLogger(__name__)

# todo -- Test rejection of bills.
#  Test fetching of bills (with the fake api?)
#  Test cancellation again

# Holds the maximum amount of invoices that can be sent in a single submission. Should most likely not change.
# Using a constant makes it easy to patch during testing to avoid needing to create 100+ invoices.
SUBMISSION_MAX_SIZE = 100
IMPORT_MAX_SIZE = 25
# An invalid invoice is considered as cancelled by the platform.
CANCELLED_STATES = {'invalid', 'cancelled'}

NAMESPACES = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
    None: 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
}


class AccountMove(models.Model):
    _inherit = "account.move"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_edi_file_id = fields.Many2one(
        comodel_name='ir.attachment',
        compute=lambda self: self._compute_linked_attachment_id('l10n_my_edi_file_id', 'l10n_my_edi_file'),
        depends=['l10n_my_edi_file'],
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_my_edi_file = fields.Binary(
        string='MyInvois XML File',
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_my_edi_display_tax_exemption_reason = fields.Boolean(
        compute='_compute_l10n_my_edi_display_tax_exemption_reason',
        string="Display Tax Exemption Reason",
        export_string_translation=False,
    )
    l10n_my_edi_exemption_reason = fields.Char(
        string="Tax Exemption Reason",
        help="Buyer’s sales tax exemption certificate number, special exemption as per gazette orders, etc.\n"
             "Only applicable if you are using a tax with a type 'Exempt'.",
    )
    l10n_my_edi_custom_form_reference = fields.Char(
        string="Customs Form Reference Number",
        help="Reference Number of Customs Form No.1, 9, etc.",
    )
    # False => Not sent yet.
    l10n_my_edi_state = fields.Selection(
        string='MyInvois State',
        help='State of this invoice on the MyInvois portal.\nAn invoice awaiting validation will be automatically updated once the validation status is available.',
        selection=[
            ('in_progress', 'Validation In Progress'),
            ('valid', 'Valid'),
            ('rejected', 'Rejected'),  # Technically not a state on MyInvois, but having it here helps with managing bills.
            ('invalid', 'Invalid'),
            ('cancelled', 'Cancelled'),
        ],
        copy=False,
        readonly=True,
        tracking=True,
        export_string_translation=False,
    )
    # Users have 72h after the validation of an invoice to cancel it. Passed that time, they need to issue a credit or debit note.
    l10n_my_edi_validation_time = fields.Datetime(
        string='Validation Time',
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_my_edi_submission_uid = fields.Char(
        string='Submission UID',
        help="Unique ID assigned to a batch of invoices when sent to MyInvois.",
        copy=False,
        readonly=True,
    )
    l10n_my_edi_external_uuid = fields.Char(
        string="MyInvois ID",
        help="Unique ID assigned to a specific invoice when sent to MyInvois.",
        copy=False,
        index=True,
        readonly=True,
    )
    # In case of error, we will use the hash as they ask to avoid resending identical invoice.
    l10n_my_error_document_hash = fields.Char(
        string="Document Hash",
        copy=False,
        readonly=True,
        export_string_translation=False,
    )
    l10n_my_edi_retry_at = fields.Char(
        string="Document Retry At",
        copy=False,
        readonly=True,
        export_string_translation=False,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('l10n_my_edi_state')
    def _compute_need_cancel_request(self):
        # EXTENDS 'account'
        super()._compute_need_cancel_request()

    @api.depends('l10n_my_edi_state')
    def _compute_show_reset_to_draft_button(self):
        # EXTEND 'account'
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda m: m.l10n_my_edi_state and m.l10n_my_edi_state not in CANCELLED_STATES).show_reset_to_draft_button = False

    @api.depends('company_id', 'invoice_line_ids.tax_ids')
    def _compute_l10n_my_edi_display_tax_exemption_reason(self):
        """ Some users will never use tax-exempt taxes, so it's better to only show the field when necessary. """
        for move in self:
            should_display = move._l10n_my_edi_uses_edi() and any(tax.l10n_my_tax_type == 'E' for tax in move.invoice_line_ids.tax_ids)
            move.l10n_my_edi_display_tax_exemption_reason = should_display

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def button_request_cancel(self):
        # EXTENDS 'account'
        super().button_request_cancel()

        if self._need_cancel_request() and self.l10n_my_edi_state == "valid":
            self._l10n_my_edi_check_can_update_status()

            return {
                "name": _("Cancel Document"),
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "l10n_my_edi.document.status.update",
                "target": "new",
                "context": {
                    "default_invoice_id": self.id,
                    "default_new_status": 'cancelled',
                },
            }

        return super().button_request_cancel()

    def button_draft(self):
        # EXTENDS 'account'

        # If the invoice has been completely cancelled, we allow resetting to draft to ease the process to reissue the invoice.
        # Not that it may be preferable to leave the invoice as cancelled, and issue a new one instead.
        invoices_to_reset = self.filtered(
            lambda i: (i.state == 'cancel' and i.l10n_my_edi_state in CANCELLED_STATES)
        )
        res = super().button_draft()
        # We do not reset the hash and retry time, as an invalid invoice that is being re-sent must be modified (hash should change)
        invoices_to_reset.write({
            'l10n_my_edi_state': False,
            'l10n_my_edi_validation_time': False,
            'l10n_my_edi_submission_uid': False,
            'l10n_my_edi_external_uuid': False,
        })
        invoices_to_reset.l10n_my_edi_file_id.unlink()
        return res

    def _need_cancel_request(self):
        # EXTENDS 'account'
        # For the in_progress state, we do not want to allow resetting to draft nor cancelling. We need to wait for the result first.
        return super()._need_cancel_request() or self.l10n_my_edi_state == 'valid'

    # --------------
    # Action methods
    # --------------

    def action_l10n_my_edi_update_status(self):
        self.ensure_one()
        status, messages = self._l10n_my_edi_fetch_status()
        # We build a message with all the errors if needed:
        if messages:
            message = self.env['account.move.send']._format_error_html({
                'error_title': _('The validation failed with the following errors:'),
                'errors': messages,
            })
        else:
            message = None
        self._l10n_my_edi_set_status(status, message)

    def action_l10n_my_edi_reject_bill(self):
        self.ensure_one()

        if self.l10n_my_edi_state == "valid":
            self._l10n_my_edi_check_can_update_status()

            return {
                "name": _("Reject Document"),
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "l10n_my_edi.document.status.update",
                "target": "new",
                "context": {
                    "default_invoice_id": self.id,
                    "default_new_status": 'rejected',
                },
            }

    def action_validate_tin(self):
        self.ensure_one()
        self.partner_id.action_validate_tin()

    # ----------------
    # Business methods
    # ----------------

    # API methods

    def _l10n_my_edi_submit_documents(self, xml_contents):
        """ Contact our IAP service in order to send the invoice xml to the MyInvois API. """
        proxy_user = self._l10n_my_edi_ensure_proxy_user()

        # We really only care about moves that appears in the xml contents.
        moves_to_send = self.filtered(lambda move: move in xml_contents)
        if not moves_to_send:
            return None

        # Ensure to lock the records that will be sent, to avoid risking sending them twice.
        self.env['res.company']._with_locked_records(moves_to_send)

        errors = {}
        success_messages = {}
        move_to_cancel = self.env['account.move']

        # MyInvois only supports up to 100 invoice per submission. To avoid timing out on big batches, we split it client side.
        for move_batch in split_every(SUBMISSION_MAX_SIZE, moves_to_send.ids, self.env['account.move'].browse):
            move_per_id = {move.id: move for move in move_batch}
            if proxy_user.edi_mode == 'demo':
                batch_result = {
                    'submission_id': sum(move_batch.ids),
                    'documents': [{
                        'move_id': move.id,
                        'uuid': move.id,  # Doesn't really matter for testing.
                        'success': True,
                    } for move in move_batch]
                }
            else:
                batch_result = proxy_user._l10n_my_edi_contact_proxy(
                    endpoint='api/l10n_my_edi/1/submit_invoices',
                    params={
                        'documents': [{
                            'move_id': move.id,
                            'move_name': move.name,
                            'error_document_hash': move.l10n_my_error_document_hash,
                            'retry_at': move.l10n_my_edi_retry_at,
                            'data': base64.b64encode(xml_contents[move].encode()).decode(),
                        } for move in move_batch]
                    }
                )

            # If an error is present in the result itself (and not per invoice), it means that the whole submission failed.
            # We don't add to the result but instead directly in the errors.
            if 'error' in batch_result:
                error_string = self._l10n_my_edi_map_error(batch_result['error'])
                errors.update({move: [error_string] for move in move_batch})
            else:
                for document_result in batch_result['documents']:
                    move = move_per_id[document_result['move_id']]
                    success = document_result['success']

                    updated_values = {
                        'l10n_my_edi_external_uuid': document_result.get('uuid'),  # rejected documents do not have a uuid.
                        'l10n_my_edi_submission_uid': batch_result['submission_uid'],
                        'l10n_my_edi_state': 'in_progress' if success else 'invalid',
                    }

                    if success:
                        # Ids are logged for future references. An invalid invoice may be reset to resend it after correction, which would be a new submission/uuid.
                        success_messages[move.id] = _('The invoice has been sent to MyInvois with uuid "%(uuid)s" and submission id "%(submission_id)s".\nValidation results will be available shortly.',
                                                      uuid=document_result['uuid'], submission_id=batch_result['submission_uid'])
                    else:
                        # When we raise a "hash_resubmitted" error, we don't resend the same hash/retry at and don't want to rewrite.
                        if 'error_document_hash' in document_result:
                            updated_values.update({
                                'l10n_my_error_document_hash': document_result['error_document_hash'],
                                'l10n_my_edi_retry_at': document_result['retry_at'],
                            })
                        errors[move] = [self._l10n_my_edi_map_error(error) for error in document_result['errors']]
                        move_to_cancel |= move

                    move.write(updated_values)

            if self._can_commit():
                self._cr.commit()

        # For successful moves, we log the sending here. Any errors will be handled by the send & print wizard.
        if success_messages:
            self.env['account.move'].browse(list(success_messages.keys()))._message_log_batch(
                bodies=success_messages,
            )

        if move_to_cancel:
            # Invalid moves should be considered as cancelled; they need to be reset to draft, corrected and sent again.
            move_to_cancel._l10n_my_edi_cancel_moves()

        return errors

    def _l10n_my_edi_fetch_updated_statuses(self):
        """
        Contact our IAP service in order to get the status of the invoices in self.
        Statuses are fetched in batches using the l10n_my_edi_submission_uid field.
        One batch is at most 100 invoices.

        Note that this is only expected to be used during the submission flow, and not later.
        """
        proxy_user = self._l10n_my_edi_ensure_proxy_user()

        # In demo, we just set everything to valid.
        if proxy_user.edi_mode == 'demo':
            self.l10n_my_edi_state = 'valid'
            return False

        self.env['res.company']._with_locked_records(self)

        errors = {}
        any_in_progress = False
        invalid_moves = self.env['account.move']
        for submission_uid, move_batch in self.grouped('l10n_my_edi_submission_uid').items():
            if not submission_uid:
                continue  # While it should never happen, it does not hurt to ensure that we won't try anything in such cases.

            result = proxy_user._l10n_my_edi_contact_proxy(
                endpoint='api/l10n_my_edi/1/get_submission_statuses',
                params={
                    'submission_uid': submission_uid
                }
            )

            if 'error' in result:
                error_string = self._l10n_my_edi_map_error(result['error'])
                errors.update({move: [error_string] for move in move_batch})
                continue

            statuses = result.get('statuses', {})
            for move in move_batch:
                status_info = statuses.get(move.l10n_my_edi_external_uuid)
                # If the status did not change, we do not need to do anything.
                if not status_info or move.l10n_my_edi_state == status_info['status']:
                    continue

                move.l10n_my_edi_state = status_info['status']
                if move.l10n_my_edi_state == 'invalid':
                    invalid_moves |= move
                    # Most of the time no reason is provided, but this is not useful. So we will fetch the exact errors individually.
                    if status_info.get('reason'):
                        errors[move] = [_('The MyInvois platform returned an "Invalid" status for this invoice for reason: %(reason)s', reason=status_info['reason'])]
                    else:
                        _status, messages = move._l10n_my_edi_fetch_status()
                        errors[move] = messages
                elif move.l10n_my_edi_state == 'in_progress':
                    # Technically at this point we expect all invoices to be processed.
                    any_in_progress = True
                    errors[move] = [_('The MyInvois platform is still processing your invoice, and we cannot send it by mail until it is done.\n'
                                      'Please retry later once the processing is done.')]
                elif move.l10n_my_edi_state == 'valid':
                    # We receive a timezone_aware datetime, but it should always be in UTC.
                    # Odoo expect a timezone unaware datetime in UTC, so we can safely remove the info without any more work needed.
                    utc_tz_aware_datetime = dateutil.parser.isoparse(status_info['valid_datetime'])
                    move.l10n_my_edi_validation_time = utc_tz_aware_datetime.replace(tzinfo=None)

            if self._can_commit():
                self._cr.commit()

        # We don't consider these errors per-say. From my understanding an invalid invoice is considered as cancelled,
        # so a new one must be issued.
        # For ease of use, we allow an invalid invoice to be reset to draft, but this will erase all links to the previously
        # cancelled invoice.
        if errors:
            # According to their documentation, you cannot cancel an already invalid invoice (they are considered cancelled by default)
            # It makes sense to consider these cancelled in Odoo too, for simplicity.
            invalid_moves._l10n_my_edi_cancel_moves()

        # Invalid or in progress invoices must return errors to stop the email sending/...
        return errors, any_in_progress

    def _l10n_my_edi_update_document(self, status, reason):
        """ Sent invoices can be cancelled, and received bills can be rejected up to 72h after validation.

        This method will try to update the status of a document on the platform, and if needed also the status in Odoo.

        There is no "Rejected" status on the platform. The document stays as 'valid' until action is taken by the vendor.
        At that point, the invoice will be cancelled if need be by the call to _l10n_my_edi_set_status.
        """
        self.ensure_one()
        self.env['res.company']._with_locked_records(self)
        proxy_user = self._l10n_my_edi_ensure_proxy_user()

        # While we do this check before opening the wizard (to avoid filling the wizard for nothing), it is safer to
        # recheck here in case we exceeded the limit in the meantime or if this is called from elsewhere.
        self._l10n_my_edi_check_can_update_status()

        successfully_updated_invoices = self.env['account.move']
        for document in self:
            result = proxy_user._l10n_my_edi_contact_proxy(
                endpoint='api/l10n_my_edi/1/update_status',
                params={
                    'status_values': {
                        'uuid': document.l10n_my_edi_external_uuid,
                        'reason': reason,
                        'status': status,
                    },
                },
            )

            # If it is not a success, it will have raised an error.
            if 'error' in result:
                self._message_log(body=self._l10n_my_edi_map_error(result['error']))
            else:
                successfully_updated_invoices |= document

        if status in self._fields['l10n_my_edi_state'].get_values(self.env):
            successfully_updated_invoices._l10n_my_edi_set_status(
                state=status,
                message=_('This invoice has been %(status)s for reason: %(reason)s', status=status, reason=reason),
            )

        if self._can_commit():
            self._cr.commit()

    @api.model
    def _cron_l10n_my_edi_synchronize_myinvois(self):
        """
        This method is to be called by a cron, and will query the Proxy in order to get the invoices issued and
        received in the last 3.5 days. (After 72h, status won't update anymore and the additional time due to
        the cron running only once an hour.)
        For both invoice types, we will check if the status need to be updated and do so if required.
        For received invoices, we will also create the moves if we do not have them in the system yet.

        Note that receiver can only get invoices for status valid or cancelled.
        Issuers can retrieve any status.

        Note that this endpoint is limited to 1 Request every 2 Seconds, so if we receive a continuationToken, we will
        wait 2 seconds before retrying.

        ⚠️ search params must be the same as the original search when using a continuationToken
        ⚠️ Note that at the time of writing, no sandbox API exists for this besides a "temporary" one that is not enough
        test properly.
        """
        # We will update all statuses, and import up to 25 invoices, for each proxy clients.
        # If there are more awaiting, we'll trigger the cron again.
        re_trigger_cron = False
        for proxy_user in self.env['account_edi_proxy_client.user'].search([('proxy_type', '=', 'l10n_my_edi')]):
            proxy_user = proxy_user.with_company(proxy_user.company_id)

            # Sent invoices is a mapping between the uuid and the current state.
            # Received is only a list of uuid to use later to fetch invoices data.
            sent_invoices = {}
            received_invoices = {}
            # For a single user, we use the same params to search for invoices.
            # We will get all recent invoices (most likely, not that many) each time but won't always process them all.
            # As we need to resend the same params each time, we can't set them on the proxy but the proxy will ensure that
            # the provided dates are as expected to avoid abuses.
            search_params = {
                'submission_from': (datetime.datetime.now(tz=UTC) - relativedelta(hours=74)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'submission_to': datetime.datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'continuation_token': '',
            }

            while True:
                search_response = proxy_user._l10n_my_edi_contact_proxy(
                    endpoint='api/l10n_my_edi/1/search_invoices',
                    params={'search_params': search_params}
                )

                # Would only happen if there is an API issue, or the params have been tampered with.
                if 'error' in search_response:
                    error_string = self._l10n_my_edi_map_error(search_response['error'])
                    raise UserError(error_string)

                sent_invoices.update(search_response['sent_invoices'])
                received_invoices.update(search_response['received_invoices'])

                if self._can_commit():
                    self._cr.commit()

                if search_response.get('continuation_token'):
                    search_params['continuation_token'] = search_response['continuation_token']
                    # searching is limited to one request every two seconds.
                    time.sleep(2)
                else:
                    break

            # Update all sent invoices.
            if sent_invoices:
                self._l10n_my_edi_update_sent_invoices_status(sent_invoices)
            # And import the first 25 received invoices.
            if received_invoices:
                re_trigger = self._l10n_my_edi_import_invoices(received_invoices, proxy_user.company_id)
                re_trigger_cron = re_trigger_cron or re_trigger

        if re_trigger_cron:
            self.env.ref('l10n_my_edi.ir_cron_myinvois_sync')._trigger()

    def _l10n_my_edi_import_invoices(self, received_bills, company):
        """
        Upon receiving invoices, we will import the first 25 non-yet-imported invoices.
        If we have more invoices to import than that, we will re-trigger the cron.

        We receive most API information, but not the file to import. This one need to be queried individually.
        """
        received_bill_uuids = list(received_bills.keys())
        existing_bills = self.env['account.move'].search([('l10n_my_edi_external_uuid', 'in', received_bill_uuids)])
        # We first loop on existing invoices, to see if we need to update the status.
        for bill in existing_bills:
            status = received_bills.pop(bill.l10n_my_edi_external_uuid, {}).get('status')
            if status and bill.l10n_my_edi_state != status:
                bill._l10n_my_edi_set_status(status)

        imported_bill_count = 0
        for bill in received_bills.values():
            if imported_bill_count >= IMPORT_MAX_SIZE:
                break
            self._l10n_my_edi_import_from_myinvois(
                uuid=bill['uuid'],
                type_name=bill['type_name'],
                status=bill['status'],
                submission_uid=bill['submission_uid'],
                company=company,
            )
            imported_bill_count += 1
        # At this point received bills is only the one non-existing in Odoo. If we have more than what we imported,
        # we want to re-trigger the cron.
        return len(received_bills) > imported_bill_count

    def _l10n_my_edi_get_document_file(self, uuid):
        """ Query the API to get the document file that was used when importing to MyInvois. """
        proxy_user = self._l10n_my_edi_ensure_proxy_user()

        if proxy_user.edi_mode == 'demo':
            return  # Technically this should not be called in demo.

        result = proxy_user._l10n_my_edi_contact_proxy(
            endpoint='api/l10n_my_edi/1/get_document_file',
            params={
                'document_uuid': uuid,
            },
        )

        if 'error' in result:
            error_string = self._l10n_my_edi_map_error(result['error'])
            raise UserError(error_string)

        if self._can_commit():
            self._cr.commit()

        return result['document'], result['validation_time']

    def _l10n_my_edi_fetch_status(self):
        """ Action to fetch the status of a single invoice. """
        self.ensure_one()
        proxy_user = self._l10n_my_edi_ensure_proxy_user()

        if proxy_user.edi_mode == 'demo':
            return  # Technically this should not be called in demo.

        result = proxy_user._l10n_my_edi_contact_proxy(
            endpoint='api/l10n_my_edi/1/get_status',
            params={
                'document_uuid': self.l10n_my_edi_external_uuid,
            },
        )

        if 'error' in result:
            error_string = self._l10n_my_edi_map_error(result['error'])
            raise UserError(error_string)

        messages = None
        if 'validation_errors' in result:
            messages = result['validation_errors']
        elif result['status_reason']:
            messages = result['status_reason']

        if self._can_commit():
            self._cr.commit()

        return result['status'], messages

    # Other methods

    def _l10n_my_edi_uses_edi(self):
        """ Helper that returns true if the invoices company is using the Malaysian EDI.
        It does not mean that this specific invoice will use it, though.
        """
        self.ensure_one()
        proxy_user = self.company_id.l10n_my_edi_proxy_user_id
        return proxy_user and proxy_user.proxy_type == 'l10n_my_edi'

    def _l10n_my_edi_generate_invoice_xml(self):
        """ This edi's file is basically an ubl 2.1 file with some specificities. """
        self.ensure_one()
        return self.env['account.edi.xml.ubl_myinvois_my']._export_invoice(self)

    def _l10n_my_edi_ensure_proxy_user(self):
        # We need this fallback, as this method could be called by a cron.
        company = self.company_id or self.env.company

        proxy_user = company.l10n_my_edi_proxy_user_id
        if not proxy_user:
            raise UserError(_("Please register for the E-Invoicing service in the settings first."))

        return proxy_user

    def _l10n_my_edi_set_status(self, state, message=None):
        """ Small helper that changes the status, and log a message if a reason is provided. """
        if message:
            self._message_log_batch(bodies={move.id: message for move in self})

        self.l10n_my_edi_state = state

        # Once invalid, an invoice is not acceptable by the platform.
        # An invalid invoice will never be visible by a customer and should, from my understanding, be considered void.
        # In Odoo, the best way to represent that is by cancelling the invoice.
        if state in CANCELLED_STATES:
            self._l10n_my_edi_cancel_moves()

    def _l10n_my_edi_check_can_update_status(self):
        """ The document status can only be updated (for rejection, or cancellation) up to 72h after the validation time.
        After that, any update will be rejected by the platform, as you are expected to issue a debit/credit note.

        This helper will raise if the status cannot be updated.
        """
        self.ensure_one()
        if not self.l10n_my_edi_validation_time:
            return

        time_difference = datetime.datetime.now() - self.l10n_my_edi_validation_time
        if time_difference >= datetime.timedelta(days=3):
            raise UserError(_('It has been more than 72h since the invoice validation, you can no longer cancel it.\n'
                              'Instead, you should issue a debit or credit note.'))

    @api.model
    def _l10n_my_edi_map_error(self, error):
        """ This helper will take in an error code coming from the proxy, and return a translatable error message. """
        error_map = {
            # These errors should be returned when we send malformed request to the EDI, ... tldr; this should never happen unless we have bugs.
            'internal_server_error': _('Server error; If the problem persists, please contact the Odoo support.'),
            # The proxy user credentials are either incorrect, or Odoo does not have the permission to invoice on their behalf.
            'invalid_tin': _('Please make sure that your company TIN is correct, and that you gave Odoo sufficient permissions on the MyInvois platform.'),
            # The api rate limit has been reached. If this happens, we need to ask the user to wait. This is also handled proxy side to be safe
            'rate_limit_exceeded': _('The api request limit has been reached. Please wait until %(limit_reset_datetime)s to try again.',
                                     limit_reset_datetime=error.get('data')),  # Note, should be UTC. The TZ name is present in the formatted date.
            'hash_resubmitted': _('This document has already been submitted and was deemed invalid.\n'
                                  'Please correct the document based on the previous error, or wait before retrying.'),
            # This happens when the MyInvois TIN validator cannot validate the TIN of the user using the provided identification type and number.
            'document_tin_not_found': _('MyInvois could not match your TIN with the identification information you provided on the company.'),
            # This happens when the TIN of the supplier doesn't match with the TIN registered on the Proxy. Data contains the TIN.
            'document_tin_mismatch': _("The TIN number of the supplier in the invoices does not match with the one provided at the time of registering for the e-invoice service.\n"
                                       "If the TIN of the supplier's record changed after that, you will need to archive your EDI Proxy User and re-register.\n"
                                       "The TIN found in the document is %(tin_number)s",
                                       tin_number=error.get('data')),
            # This happens when a batch of invoices contains multiple different identifier for the supplier. Data contains the invoice.
            'multiple_documents_id': _('Multiple different supplier identification information were found in the invoices.\n'
                                       'If the company identification information changed, you may need to delete your invoice attachments and regenerate them.'),
            # Same as the previous error, but with the supplier TIN
            'multiple_documents_tin': _('Multiple different supplier TIN were found in the invoices.\n'
                                        'If the company TIN changed, you may need to delete your invoice attachments and regenerate them.'),
            # You cannot cancel an invoice that has been rejected or that is invalid
            'update_incorrect_state': _('You can only update the status of invoices in the valid state.'),
            'update_period_over': _('It has been more than 72h since the invoice validation, you can no longer update it.\n'
                                    'Instead, you should issue or request a debit or credit note.'),
            'update_active_documents': _('You cannot update this invoice, has it has been referenced by a debit or credit note.\n'
                                         'If you still want to update it, you must first update the debit/credit note.'),
            'update_forbidden': _('You do not have the permission to update this invoice.'),
            'search_date_invalid': _('The search params are invalid.'),  # Should never happen
        }

        if error.get('target'):
            # When validating a part of the invoice, they give random numerical codes with no explanation whatsoever.
            # So instead of trying to guess what they mean, we just give a generic "this is not valid" error and hope for the best.
            # For future bugfixer => To avoid issues as much as possible, please add additional checks in the UBL python file to avoid these.
            return _('An error occurred while validating the invoice: "%(property_name)s" is invalid.', property_name=error['target'])

        return error_map.get(error['reference'], _("An unexpected error has occurred."))

    def _l10n_my_edi_update_sent_invoices_status(self, sent_invoices):
        """
        With a list of sent data and statuses, this will ensure that invoices sent to MyInvois have their
        status updated if it is needed.

        todo once properly testable, we may need to query the detail api to get the details of validation errors
        """
        sent_invoices_uuids = list(sent_invoices.keys())
        invoices_to_update = self.env['account.move'].search([('l10n_my_edi_external_uuid', 'in', sent_invoices_uuids)])
        for invoice in invoices_to_update:
            status = sent_invoices.get(invoice.l10n_my_edi_external_uuid)
            if status and invoice.l10n_my_edi_state != status:
                invoice._l10n_my_edi_set_status(status)

    def _l10n_my_edi_import_from_myinvois(self, uuid, type_name, status, submission_uid, company):
        """ This method will take the data of a file coming from myinvois (xml, or json) and then create an invoice
        based on it.
        """
        def is_json(document_string):
            try:
                json.loads(document_string)
            except ValueError as _e:
                return False
            return True

        def is_xml(document_string):
            try:
                etree.fromstring(document_string)
            except ParseError as _e:
                return False
            return True

        # 1. Get the file from the platform. This is a string representing either a json, or a xml.
        document_string, validation_time = self._l10n_my_edi_get_document_file(uuid)  # the validation time is not available from the search endpoint...

        # 2. If we received a json, we transform it in XML.
        if is_json(document_string):
            document_string = self._l10n_my_edi_convert_json_to_xml(document_string)

        # We then ensure that we are actually working with a xml as expected.
        if not is_xml(document_string):
            raise UserError(_('Could not import the document with uuid %(uuid)s: unknown file format.', uuid=uuid))

        # 3. Get the invoice type.
        if type_name == '01':
            move_type = 'in_invoice'
        elif type_name == '02':
            move_type = 'in_refund'
        elif type_name == '03':
            # debit note
            move_type = 'in_invoice'
        else:
            raise UserError(_('Could not import the document with uuid %(uuid)s: unknown file type.', uuid=uuid))

        # 3. Import the file data.
        move_data = {
            'move_type': move_type,
        }

        if company.l10n_my_edi_default_import_journal_id.id:
            move_data['journal_id'] = company.l10n_my_edi_default_import_journal_id.id

        move = self.env['account.move'].create(move_data)
        try:
            with self.env.cr.savepoint():
                with move._get_edi_creation() as move:
                    # pylint: disable=not-callable
                    success = self.env['account.edi.xml.ubl_myinvois_my']._import_invoice_ubl_cii(
                        invoice=move,
                        file_data={
                            'xml_tree': etree.fromstring(document_string),
                        }
                    )
                if success:
                    move._link_bill_origin_to_purchase_orders(timeout=4)
                    move.write({
                        'l10n_my_edi_state': status,
                        'l10n_my_edi_validation_time': dateutil.parser.isoparse(validation_time).replace(tzinfo=None),
                        'l10n_my_edi_submission_uid': submission_uid,
                        'l10n_my_edi_external_uuid': uuid,
                    })
                    if self.env['account.move.send']._can_commit():
                        self.env.cr.commit()
        except RedirectWarning:
            raise
        except Exception as _e:
            message = _("Error importing attachment '' as invoice (decoder=)")
            move.sudo().message_post(body=message)
            _logger.exception(message)

        return move

    def _l10n_my_edi_convert_json_to_xml(self, document_string):
        """ In practice, the json file is strictly following the UBL format.
        Instead of rewriting the whole import logic, we will transform that json into a xml and import that.

        https://docs.oasis-open.org/ubl/UBL-2.1-JSON/v2.0/cnd01/UBL-2.1-JSON-v2.0-cnd01.xml

        Note that signature stuff are being ignored while importing, as namespacing them would be difficult.
        The format is also the one exported to the platform by the seller, so this could need some tweaks depending on the way it's sent.
        """
        # We start by loading the json
        json_data = json.loads(document_string)
        invoice_data = json_data['Invoice']

        # The logic is as follows: if an element has sub-elements, it is using the CAC namespace. If not, it is using CBC.
        # For CAC elements, if multiples are present (e.g. multiple invoice lines) you will file a single InvoiceLine element with multiple child items.
        root = self._l10n_my_make_sub_element('Invoice', invoice_data[0], root=True)
        return etree.tostring(root).decode()

    def _l10n_my_make_sub_element(self, element_name, element_data, root=False):
        """ Add a given node, to the given element.
        Used recursively to populate the xml tree from the root, based on the given json element
        """
        # These are not relevant to the import of invoices, and it would be hard to transform these
        node_to_ignore = ['UBLExtensions', 'Signature']

        # Start by making the element
        is_leaf = not any(isinstance(value, list) for value in element_data.values())
        if not root:
            if is_leaf:
                element_name = f"{{{NAMESPACES.get('cbc')}}}{element_name}"
            else:
                element_name = f"{{{NAMESPACES.get('cac')}}}{element_name}"

        namespaces = None
        if root:
            namespaces = NAMESPACES

        if not is_leaf:
            # A leaf could have attributes. In this case, they are elements that are not lists.
            element = etree.Element(element_name, nsmap=namespaces)
            for sub_element_name, sub_element_data in element_data.items():
                if sub_element_name in node_to_ignore:
                    continue

                if isinstance(sub_element_data, list):
                    for sub_element in sub_element_data:
                        element.append(self._l10n_my_make_sub_element(sub_element_name, sub_element))
                else:
                    # It's actually an attribute
                    element.set(sub_element_name, sub_element_data)
        else:
            # the '_' key hold the text, while 'named' key hold the attribute
            value = element_data.pop('_', '')
            # The remaining data are attributes and their value. They can be passed to Element to build the element
            element = etree.Element(element_name, **element_data, nsmap=namespaces)
            if not isinstance(value, str):
                value = str(value)
            element.text = value

        return element

    def _l10n_my_edi_cancel_moves(self):
        """ Try to cancel the moves in self if allowed by the lock date. """
        for move in self:
            try:
                move._check_fiscalyear_lock_date()
                move.line_ids._check_tax_lock_date()
                move.button_cancel()
            except UserError as e:
                move.with_context(no_new_invoice=True).message_post(
                    body=_(
                        'The invoice has been canceled on MyInvois, '
                        'But the cancellation in Odoo failed with error: %(error)s\n'
                        'Please resolve the problem manually, and then cancel the invoice.', error=e
                    )
                )
