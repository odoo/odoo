# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
import time

import dateutil

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import split_every

_logger = logging.getLogger(__name__)

# Holds the maximum amount of invoices that can be sent in a single submission. Should most likely not change.
# Using a constant makes it easy to patch during testing to avoid needing to create 100+ invoices.
SUBMISSION_MAX_SIZE = 100
MAX_SUBMISSION_UPDATE = 25
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
        help="""Reference Number of Customs Forms
Customs form No. 2 for Customer Invoices
Customs form No. 1, 9, etc for Vendor Bills""",
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

        if self._need_cancel_request() and self.l10n_my_edi_state in ['valid', 'rejected']:
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

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append('l10n_my_edi_file')
        return fields_list

    def _need_cancel_request(self):
        # EXTENDS 'account'
        # For the in_progress state, we do not want to allow resetting to draft nor cancelling. We need to wait for the result first.
        return super()._need_cancel_request() or self.l10n_my_edi_state in ['valid', 'rejected']

    # --------------
    # Action methods
    # --------------

    def action_l10n_my_edi_update_status(self):
        self.ensure_one()
        result = self._l10n_my_edi_fetch_status()

        # This is called manually by the user. In case of errors, we will raise.
        # If the validation failed or the invoice has been rejected/cancelled, we will log the result in the chatter.
        if 'error' in result:
            raise UserError(self._l10n_my_edi_map_error(result['error']))

        # If there has been no status change, we do not want to do anything.
        if result['status'] == self.l10n_my_edi_state:
            return

        if 'validation_errors' in result:
            validation_error = self.env['account.move.send']._format_error_html({
                'error_title': _('The validation failed with the following errors:'),
                'errors': result['validation_errors'],
            })
            self._l10n_my_edi_set_status(result['status'], validation_error)
        elif result.get('status_reason'):
            self._l10n_my_edi_set_status(
                result['status'],
                message=_('This invoice has been %(status)s for reason: %(reason)s', status=result['status'], reason=result['status_reason']),
            )
        else:
            self._l10n_my_edi_set_status(result['status'])

        # As done during submission flow, when the status becomes
        if self.l10n_my_edi_state == 'valid':
            self._update_validation_fields(result)

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

    def _l10n_my_edi_submit_documents(self, xml_contents, commit=True):
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

            if commit and self._can_commit():
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

    def _l10n_my_edi_fetch_updated_statuses(self, commit=True):
        """
        Contact our IAP service in order to get the status of the invoices in self.
        Statuses are fetched in batches using the l10n_my_edi_submission_uid field.
        One batch is at most 100 invoices.

        Note that this is only expected to be used during the submission flow, and not later.
        """
        proxy_user = self._l10n_my_edi_ensure_proxy_user()

        self.env['res.company']._with_locked_records(self)

        errors = {}
        any_in_progress = False
        invalid_moves = self.env['account.move']
        for submission_uid, move_batch in self.grouped('l10n_my_edi_submission_uid').items():
            if not submission_uid:
                continue  # While it should never happen, it does not hurt to ensure that we won't try anything in such cases.

            error, statuses = self._l10n_my_get_submission_status(submission_uid, proxy_user)

            if error:
                errors.update({move: [error] for move in move_batch})
                continue

            for move in move_batch:
                status_info = statuses.get(move.l10n_my_edi_external_uuid)
                # l10n_my_edi_state would already be in progress as its set during submission
                if ((status_info and status_info["status"] == "in_progress") or
                        (not status_info and move.l10n_my_edi_state == "in_progress")):
                    any_in_progress = True

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
                        result = move._l10n_my_edi_fetch_status()
                        if 'error' in result:
                            errors[move] = [self._l10n_my_edi_map_error(result['error'])]
                        elif 'validation_errors' in result:
                            errors[move] = [self.env['account.move.send']._format_error_html({
                                'error_title': _('The validation failed with the following errors:'),
                                'errors': result['validation_errors'],
                            })]
                        elif result['status_reason']:
                            errors[move] = [result['status_reason']]
                elif move.l10n_my_edi_state == 'valid':
                    move._update_validation_fields(status_info)

            if commit and self._can_commit():
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
        This cron is based on the recommended method to fetch the status of the documents according to their doc.
        MAX_SUBMISSION_UPDATE defines how many submissions to process in a single cron run.
        """
        # First step is to get the invoices for which the status is not yet final.
        # A invoice whose status will not change anymore is: (cancelled or invalid) or has been validated more than 74h ago.
        # /!\ when an invoice validation is pending, l10n_my_edi_validation_time is still None. These also need to be updated.
        datetime_threshold = datetime.datetime.now() - datetime.timedelta(hours=74)
        # We always want to fetch in_progress invoices, it's very likely that their status is already there.
        invoice_domain = [("l10n_my_edi_state", "=", "in_progress")]
        # For valid invoices, we want them if their l10n_my_edi_validation_time is less than 74h ago, and if their l10n_my_edi_retry_at in the past.
        invoice_domain = expression.OR([invoice_domain, [
            ('l10n_my_edi_state', '=', 'valid'),
            ('l10n_my_edi_validation_time', '>', datetime_threshold),
            '|',
            ('l10n_my_edi_retry_at', '<=', datetime.datetime.now()),
            ('l10n_my_edi_retry_at', '=', False),
        ]])
        grouped_invoices = self.env["account.move"]._read_group(
            invoice_domain,
            groupby=["company_id", "l10n_my_edi_submission_uid"],
            aggregates=["id:recordset"],
            limit=MAX_SUBMISSION_UPDATE,
        )
        invoice_count = self.search_count(invoice_domain)  # Count the total amount of invoices to process.

        processed_invoices = 0
        for company, submission_uid, invoices in grouped_invoices:
            if not company.l10n_my_edi_proxy_user_id:
                continue

            error, status_fetch_result = self._l10n_my_get_submission_status(
                submission_uid, company.l10n_my_edi_proxy_user_id
            )
            if error:
                raise UserError(error)  # We do not expect errors here so raising is a correct solution.

            for invoice in invoices:
                invoice_result = status_fetch_result.get(invoice.l10n_my_edi_external_uuid)
                if not invoice_result:
                    continue

                # For valid invoices, we always want to update the try time; it's pointless to fetch too often.
                if invoice.l10n_my_edi_state == "valid" or invoice_result["status"] == "valid":
                    invoice.l10n_my_edi_retry_at = fields.Datetime.now() + datetime.timedelta(hours=1)

                if invoice_result["status"] == invoice.l10n_my_edi_state:
                    continue

                # If the state changed, we update the invoice with the new state and an eventual reason.
                invoice._l10n_my_edi_set_status(
                    state=invoice_result["status"],
                    message=_(
                        "This invoice has been %(status)s for reason: %(reason)s",
                        status=invoice_result["status"],
                        reason=invoice_result["reason"],
                    )
                    if invoice_result.get("reason")
                    else None,
                )
                if invoice.l10n_my_edi_state == "valid":
                    invoice._update_validation_fields(invoice_result)

            processed_invoices += len(invoices)
            # Commit if we can, in case an issue arises later.
            if self._can_commit():
                self.env['ir.cron']._notify_progress(done=processed_invoices, remaining=invoice_count - processed_invoices)
                self._cr.commit()

            time.sleep(0.3)  # There is a limit of how many calls we can do, so we pace ourselves
        self.env['ir.cron']._notify_progress(done=processed_invoices, remaining=invoice_count - processed_invoices)

    @api.model
    def _l10n_my_get_submission_status(self, submission_uid, proxy_user):
        """ Returns the status of all invoices in the submission.
        If there are too many and the submission is paginated, this will fetch each page with a waiting time of 1s per call.
        As a page can hold 100 invoice, it should not happen often.

        The proxy user is given as a param as this method can be called from the cron, in which case we can't rely on self.
        """
        # In case of errors, we return it alongside any results. We cannot raise as this is called from the send & print in some cases.
        error = ''
        # The api returns the result per document uuid, already correctly formated.
        # We do not need to format the data anymore for processing later but just to ensure we get complete data of the submission.
        result = proxy_user._l10n_my_edi_contact_proxy(
            endpoint='api/l10n_my_edi/1/get_submission_statuses',
            params={
                'submission_uid': submission_uid,
                'page': 1,
            }
        )

        if 'error' in result:
            error = self._l10n_my_edi_map_error(result['error'])
        else:
            if result['document_count'] <= 100:  # If so, we got all of it at once.
                result = result['statuses']
            else:
                # Otherwise we'll need to get the remaining invoices per batch of 100.
                for page in range(2, (result['document_count'] // 100) + 1):
                    time.sleep(1)  # To avoid any risks of throttling, we should wait a bit before continuing
                    page_result = proxy_user._l10n_my_edi_contact_proxy(
                        endpoint='api/l10n_my_edi/1/get_submission_statuses',
                        params={
                            'submission_uid': submission_uid,
                            'page': page,
                        }
                    )
                    result['statuses'].update(page_result['statuses'])
                result = result['statuses']
        return error, result

    def _l10n_my_edi_fetch_status(self):
        """ Action to fetch the status of a single invoice. """
        self.ensure_one()
        proxy_user = self._l10n_my_edi_ensure_proxy_user()

        # What to do with the given status is to be handled by the calling code.
        return proxy_user._l10n_my_edi_contact_proxy(
            endpoint='api/l10n_my_edi/1/get_status',
            params={
                'document_uuid': self.l10n_my_edi_external_uuid,
            },
        )

    def _update_validation_fields(self, validation_result):
        """ Update a few important fields in self based on the data received when an invoice gets to the 'valid' state. """
        self.ensure_one()
        # We receive a timezone_aware datetime, but it should always be in UTC.
        # Odoo expect a timezone unaware datetime in UTC, so we can safely remove the info without any more work needed.
        utc_tz_aware_datetime = dateutil.parser.isoparse(validation_result['valid_datetime'])
        self.l10n_my_edi_validation_time = utc_tz_aware_datetime.replace(tzinfo=None)

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
            'document_not_found': _('The document provided in the request does not exist.'),  # Should never happen
            'search_date_invalid': _('The search params are invalid.'),  # Should also never happen
            'submission_too_large': _('The submission is too large, try to send fewer invoices at once.'),
            'action_forbidden': _('Permission to do this action has not been granted. Please ensure that Odoo has sufficient permissions on the MyInvois platform.'),
        }

        if error.get('target'):
            # When validating a part of the invoice, they give random numerical codes with no explanation whatsoever.
            # So instead of trying to guess what they mean, we just give a generic "this is not valid" error and hope for the best.
            # For future bugfixer => To avoid issues as much as possible, please add additional checks in the UBL python file to avoid these.
            return _('An error occurred while validating the invoice: "%(property_name)s" is invalid.', property_name=error['target'])

        return error_map.get(error['reference'], _("An unexpected error has occurred."))

    def _l10n_my_edi_cancel_moves(self):
        """ Try to cancel the moves in self if allowed by the lock date. """
        for move in self:
            try:
                move._check_fiscal_lock_dates()
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
