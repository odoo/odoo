import base64
from datetime import date, timedelta, timezone
import logging

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.x509.extensions import ExtensionNotFound
import dateutil.parser
from dateutil.easter import easter
import pytz
from stdnum.pl.nip import compact

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date

from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError, KSeFTimeoutError
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService
from odoo.addons.l10n_pl_edi_offline.tools.ksef_latarnia_service import KsefLatarniaService

_logger = logging.getLogger(__name__)

OFFLINE_BATCH_SIZE = 10


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pl_edi_status = fields.Selection(selection_add=[
        ('offline_pending', 'Offline (Pending)'),
        ('offline_failed', 'Offline (Failed)'),
    ])
    l10n_pl_edi_offline_deadline = fields.Date(
        string="Offline24 Submission Deadline",
        readonly=True,
        copy=False,
        help="Statutory deadline for submitting this Offline24 invoice to KSeF.",
    )
    l10n_pl_edi_offline_error = fields.Char(readonly=True, copy=False)
    l10n_pl_edi_offline_next_attempt = fields.Datetime(readonly=True, copy=False)
    l10n_pl_edi_offline_prepared_at = fields.Datetime(
        string="Offline Preparation Time",
        readonly=True,
        copy=False,
    )

    @staticmethod
    def _l10n_pl_edi_add_working_days(start_date, working_days):
        def get_holidays(year):
            easter_sunday = easter(year)
            return {
                date(year, month, day)
                for month, day in (
                    (1, 1), (1, 6), (5, 1), (5, 3), (8, 15),
                    (11, 1), (11, 11), (12, 24), (12, 25), (12, 26),
                )
            } | {
                easter_sunday + timedelta(days=1),
                easter_sunday + timedelta(days=60),
            }

        deadline = start_date
        holiday_year = deadline.year
        holidays = get_holidays(holiday_year)
        while working_days:
            deadline += timedelta(days=1)
            if deadline.year != holiday_year:
                holiday_year = deadline.year
                holidays = get_holidays(holiday_year)
            if deadline.weekday() < 5 and deadline not in holidays:
                working_days -= 1
        return deadline

    @api.model
    def _l10n_pl_edi_get_offline_deadline(self, invoice_date):
        return self._l10n_pl_edi_add_working_days(invoice_date, 1)

    @staticmethod
    def _l10n_pl_edi_parse_latarnia_datetime(value):
        if not value:
            return False
        try:
            return dateutil.parser.isoparse(value).astimezone(timezone.utc).replace(tzinfo=None)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _l10n_pl_edi_get_warsaw_date(value):
        return pytz.utc.localize(value).astimezone(pytz.timezone('Europe/Warsaw')).date()

    @api.model
    def _l10n_pl_edi_get_latarnia_data(self, include_messages=False):
        service = KsefLatarniaService(self.env)
        return service.get_status(), service.get_messages() if include_messages else []

    @staticmethod
    def _l10n_pl_edi_event_overlaps_submission_period(move, event_start, event_end):
        return (
            move.l10n_pl_edi_offline_prepared_at <= event_end
            and move._l10n_pl_edi_get_warsaw_date(event_start) <= move.l10n_pl_edi_offline_deadline
        )

    def _l10n_pl_edi_apply_deadline_event(self, message, working_days, maintenance=False):
        event_start = self._l10n_pl_edi_parse_latarnia_datetime(message.get('start'))
        event_end = self._l10n_pl_edi_parse_latarnia_datetime(message.get('end'))
        if not event_start or not event_end:
            return
        event_id = message['eventId']
        deadline = self._l10n_pl_edi_add_working_days(self._l10n_pl_edi_get_warsaw_date(event_end), working_days)
        for move in self:
            prepared_at = move.l10n_pl_edi_offline_prepared_at
            event_applies = (
                event_start <= prepared_at <= event_end
                if maintenance
                else self._l10n_pl_edi_event_overlaps_submission_period(
                    move, event_start, event_end,
                )
            )
            if not event_applies:
                continue
            if move.l10n_pl_edi_offline_deadline < deadline:
                move.l10n_pl_edi_offline_deadline = deadline
                move.message_post(body=self.env._(
                    "The KSeF submission deadline was adjusted to %(deadline)s based on "
                    "availability announcement %(event)s.",
                    deadline=format_date(self.env, deadline),
                    event=event_id,
                ))

    def _l10n_pl_edi_reconcile_latarnia(self, status_data, messages, now):
        latest_messages = {}
        for message in messages or []:
            key = (message.get('eventId'), message.get('type'))
            if message.get('version', 0) >= latest_messages.get(key, {}).get('version', -1):
                latest_messages[key] = message

        for message in sorted(
            latest_messages.values(), key=lambda message: message.get('end', ''),
        ):
            event_end = self._l10n_pl_edi_parse_latarnia_datetime(message.get('end'))
            if not event_end or event_end > now:
                continue
            if message.get('category') == 'MAINTENANCE':
                self._l10n_pl_edi_apply_deadline_event(message, 1, maintenance=True)
            elif message.get('category') in ('FAILURE', 'TOTAL_FAILURE') and message.get('type') == 'FAILURE_END':
                self._l10n_pl_edi_apply_deadline_event(message, 7)

        status = (status_data or {}).get('status')
        active_message = next((
            message for message in (status_data or {}).get('messages') or []
            if message.get('category') == status
        ), {})
        if status == 'MAINTENANCE' and active_message:
            self._l10n_pl_edi_apply_deadline_event(active_message, 1, maintenance=True)
        return status, active_message

    def _l10n_pl_edi_generate_certificate_qr_link(self):
        self.ensure_one()
        certificate = self.company_id.sudo().l10n_pl_edi_offline_certificate
        invoice_hash = self._l10n_pl_edi_get_qr_hash()
        if not certificate or not certificate.private_key_id or not invoice_hash:
            return ''

        seller_nip = self._l10n_pl_edi_get_qr_xml_values()[0]
        if not seller_nip:
            return ''
        host = self._l10n_pl_edi_get_qr_host()
        company_nip = compact(self.company_id.vat)
        serial = f'{int(certificate.serial_number):016X}'
        path = f'{host}/certificate/Nip/{company_nip}/{seller_nip}/{serial}/{invoice_hash}'
        private_key_record = certificate.private_key_id.with_context(bin_size=False)
        private_key = serialization.load_pem_private_key(
            base64.b64decode(private_key_record.pem_key),
            password=None,
        )
        if isinstance(private_key, rsa.RSAPrivateKey):
            signature = private_key.sign(
                path.encode(),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
                hashes.SHA256(),
            )
        elif isinstance(private_key, ec.EllipticCurvePrivateKey):
            signature = private_key.sign(path.encode(), ec.ECDSA(hashes.SHA256()))
        else:
            raise UserError(self.env._("The KSeF offline certificate uses an unsupported private key type."))
        return f"https://{path}/{base64.urlsafe_b64encode(signature).decode().rstrip('=')}"

    def _l10n_pl_edi_generate_certificate_qr(self):
        self.ensure_one()
        return base64.b64encode(self.env['ir.actions.report'].barcode(
            barcode_type='QR', value=self._l10n_pl_edi_generate_certificate_qr_link(),
            width=180, height=180, quiet=0,
        ))

    def _l10n_pl_edi_check_mandatory_fields(self):
        # EXTENDS l10n_pl_edi
        errors = super()._l10n_pl_edi_check_mandatory_fields()
        # Without the KSeF number of the corrected invoice, the KOR XML would tell it was issued outside KSeF.
        waiting_invoices = self.filtered(lambda move: not move.l10n_pl_edi_status).reversed_entry_id.filtered(
            lambda move: move.l10n_pl_edi_status in ('offline_pending', 'offline_failed')
        )
        if waiting_invoices:
            errors['l10n_pl_edi_offline_corrected_invoice_pending'] = {
                'level': 'danger',
                'message': '\n'.join(self.env._(
                    "The corrected invoice %s is waiting for its Offline24 submission to KSeF. "
                    "Send its credit note once it is accepted.",
                    invoice.name,
                ) for invoice in waiting_invoices),
            }
        return errors

    def _l10n_pl_edi_store_offline_xml(self, xml_content):
        self.ensure_one()
        attachment = self.env['ir.attachment'].sudo().create({
            'description': self.env._('KSeF Offline Invoice XML'),
            'name': f"FA3-{self.name.replace('/', '_')}.xml",
            'mimetype': 'application/xml',
            'raw': xml_content,
            'res_id': self.id,
            'res_model': self._name,
            'res_field': 'l10n_pl_edi_attachment_file',
        })
        self.invalidate_recordset(fnames=['l10n_pl_edi_attachment_id', 'l10n_pl_edi_attachment_file'])
        self.sudo().with_context(no_new_invoice=True).message_post(
            body=self.env._("The frozen Offline24 KSeF XML has been attached."),
            attachment_ids=attachment.ids,
        )

    def _l10n_pl_edi_handle_ksef_unavailable(self, error, xml_content=None, session_id=None):
        # EXTENDS l10n_pl_edi
        if self.move_type not in ('out_invoice', 'out_refund') or not self.company_id.sudo().l10n_pl_edi_offline_certificate:
            return super()._l10n_pl_edi_handle_ksef_unavailable(error, xml_content=xml_content, session_id=session_id)
        self._l10n_pl_edi_prepare_offline(xml_content=xml_content, session_id=session_id)
        self.message_post(body=self.env._(
            "KSeF was unavailable, so the invoice was issued in Offline24. "
            "It will be submitted to KSeF automatically. Error: %s",
            error,
        ))
        return True

    def _l10n_pl_edi_prepare_offline(self, xml_content=None, session_id=None):
        """ Issue the invoice in Offline24: freeze its KSeF XML and queue it for submission.

        :param xml_content: the XML bytes already sent to KSeF by a failed online sending, frozen
            as they are instead of a new rendering so that KSeF can't receive two versions.
        :param session_id: the KSeF session of that sending, searched for the invoice before
            submitting it again.
        """
        self.ensure_one()
        if (
            self.country_code != 'PL'
            or not self.l10n_pl_edi_register
            or self.state != 'posted'
            or self.move_type not in ('out_invoice', 'out_refund')
        ):
            raise UserError(self.env._(
                "Only posted Polish customer invoices and credit notes with KSeF enabled can be prepared offline."
            ))
        certificate = self.company_id.sudo().l10n_pl_edi_offline_certificate
        if not certificate or not certificate.private_key_id or not certificate.is_valid:
            raise UserError(self.env._(
                "Configure a valid KSeF Offline certificate with its private key first."
            ))
        certificate_data = x509.load_pem_x509_certificate(base64.b64decode(
            certificate.with_context(bin_size=False).pem_certificate
        ))
        try:
            key_usage = certificate_data.extensions.get_extension_for_class(x509.KeyUsage).value
        except ExtensionNotFound:
            key_usage = None
        if not key_usage or not key_usage.content_commitment:
            raise UserError(self.env._(
                "The selected certificate must be a KSeF Offline certificate."
            ))
        if self.l10n_pl_edi_attachment_file:
            raise UserError(self.env._("This invoice already has a frozen KSeF XML document."))
        prepared_at = fields.Datetime.now()
        if not xml_content:
            xml_content = self._l10n_pl_edi_render_xml().encode()
        self.write({
            'l10n_pl_edi_status': 'offline_pending',
            'l10n_pl_edi_session_id': session_id or False,
            'l10n_pl_edi_offline_deadline': self._l10n_pl_edi_get_offline_deadline(self.invoice_date),
            'l10n_pl_edi_offline_next_attempt': prepared_at,
            'l10n_pl_edi_offline_prepared_at': prepared_at,
            'l10n_pl_edi_offline_error': False,
        })
        self._l10n_pl_edi_store_offline_xml(xml_content)
        # Only refresh an existing PDF, Send & Print or the next print renders the first one.
        if self.invoice_pdf_report_id:
            try:
                self._l10n_pl_edi_store_pdf()
            except Exception:  # noqa: BLE001
                _logger.exception("Could not render the KSeF invoice visualization for %s", self.display_name)
                self.message_post(body=self.env._(
                    "The invoice was issued in Offline24, but its PDF visualization could not be generated."
                ))
        self.env.ref('l10n_pl_edi_offline.cron_l10n_pl_edi_send_offline')._trigger()

    @api.depends('l10n_pl_edi_status')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda move: move.l10n_pl_edi_status in (
            'offline_pending', 'offline_failed'
        )).show_reset_to_draft_button = False

    def button_draft(self):
        # EXTENDS l10n_pl_edi
        if any(move.l10n_pl_edi_status in ('offline_pending', 'offline_failed') for move in self):
            raise UserError(self.env._(
                "An invoice issued in Offline24 cannot be reset to draft or canceled. "
                "Issue a credit note (correction invoice) to correct it."
            ))
        return super().button_draft()

    @api.model
    def _l10n_pl_edi_defer_offline_queue(self, moves, error, retry_at, rate_limited=False):
        move = moves[0]
        first_failure = move.l10n_pl_edi_status != 'offline_failed'
        move.write({
            'l10n_pl_edi_status': 'offline_failed',
            'l10n_pl_edi_offline_error': str(error),
            'l10n_pl_edi_offline_next_attempt': retry_at,
        })
        if rate_limited:
            moves.l10n_pl_edi_offline_next_attempt = retry_at
            move.company_id.sudo().l10n_pl_edi_offline_next_send = retry_at
        self.env.ref('l10n_pl_edi_offline.cron_l10n_pl_edi_send_offline')._trigger(at=retry_at)
        if first_failure:
            body = self.env._(
                "KSeF rate-limited the automatic submission. Odoo will resume after the "
                "requested delay. The latest error is available on the Polish "
                "extra-information page."
            ) if rate_limited else self.env._(
                "Automatic KSeF submission failed. Odoo will retry in one hour. "
                "The latest error is available on the Polish extra-information page."
            )
            move.message_post(body=body)

    def _l10n_pl_edi_apply_offline_status(self, response):
        self.ensure_one()
        status_code = response.get('status', {}).get('code')
        if not (status_values := self._l10n_pl_edi_get_status_mapping().get(status_code)):
            raise UserError(self.env._(
                "KSeF returned an unknown invoice status after the submission timed out: %s.",
                status_code,
            ))
        status, message = status_values
        self.write({
            'l10n_pl_edi_status': status,
            'l10n_pl_edi_ref': response['referenceNumber'],
            'l10n_pl_edi_number': response.get('ksefNumber'),
            'l10n_pl_edi_header': message,
            'l10n_pl_edi_offline_error': False,
            'l10n_pl_edi_offline_next_attempt': False,
        })
        self.message_post(body=message)
        if status == 'accepted' and self.invoice_pdf_report_id:
            try:
                self._l10n_pl_edi_store_pdf()
            except Exception:  # noqa: BLE001
                _logger.exception("Could not render the KSeF invoice visualization for %s", self.display_name)
                self.message_post(body=self.env._(
                    "The KSeF invoice was accepted, but its PDF visualization could not be generated."
                ))

    def _l10n_pl_edi_submit_offline(self, service):
        self.ensure_one()
        xml_content = self._l10n_pl_edi_get_xml_bytes()
        invoice_hash = service.get_invoice_hash(xml_content)
        if previous_session_id := self.l10n_pl_edi_session_id:
            if response := service.find_invoice_in_session(
                invoice_hash,
                session_id=previous_session_id,
            ):
                self._l10n_pl_edi_apply_offline_status(response)
                return
            self.l10n_pl_edi_session_id = False

        service.open_ksef_session()
        session_id = self.company_id.sudo().l10n_pl_edi_session_id
        try:
            response = service.send_invoice(xml_content, offline_mode=True)
        except KSeFTimeoutError:
            self.l10n_pl_edi_session_id = session_id
            if response := service.find_invoice_in_session(invoice_hash, session_id=session_id):
                self._l10n_pl_edi_apply_offline_status(response)
                return
            raise

        reference = response.get('referenceNumber')
        if not reference:
            raise UserError(self.env._("KSeF did not return an invoice reference number."))
        self.write({
            'l10n_pl_edi_status': 'sent',
            'l10n_pl_edi_ref': reference,
            'l10n_pl_edi_session_id': session_id,
            'l10n_pl_edi_offline_error': False,
            'l10n_pl_edi_offline_next_attempt': False,
        })
        self.message_post(body=self.env._("The offline invoice was submitted to KSeF."))
        self.env.ref('l10n_pl_edi.cron_auto_checks_the_polish_invoice_status')._trigger()

    @api.model
    def _cron_l10n_pl_edi_send_offline(self):
        now = fields.Datetime.now()
        cron = self.env.ref('l10n_pl_edi_offline.cron_l10n_pl_edi_send_offline')
        queue_domain = [('l10n_pl_edi_status', 'in', ('offline_pending', 'offline_failed'))]
        queue_order = 'l10n_pl_edi_offline_deadline ASC, invoice_date, id'
        queued = self.search(queue_domain, order=queue_order)
        if not queued:
            return

        status_data, messages = self._l10n_pl_edi_get_latarnia_data(include_messages=True)
        latarnia_status, active_message = queued._l10n_pl_edi_reconcile_latarnia(
            status_data, messages, now,
        )
        if latarnia_status in ('MAINTENANCE', 'FAILURE', 'TOTAL_FAILURE'):
            queued = queued.filtered_domain(queue_domain)
            if queued:
                event_end = self._l10n_pl_edi_parse_latarnia_datetime(active_message.get('end'))
                retry_at = event_end or now + timedelta(minutes=20)
                queued.l10n_pl_edi_offline_next_attempt = retry_at
                cron._trigger(at=retry_at)
            return

        queued = self.search(queue_domain, order=queue_order)
        pending = queued.filtered_domain([
            *queue_domain,
            ('l10n_pl_edi_offline_next_attempt', '<=', now),
        ])
        for company, moves in pending.grouped('company_id').items():
            company_sudo = company.sudo()
            next_send = company_sudo.l10n_pl_edi_offline_next_send
            if next_send and next_send > now:
                moves.l10n_pl_edi_offline_next_attempt = next_send
                cron._trigger(at=next_send)
                continue
            service = KsefApiService(company)
            batch = moves[:OFFLINE_BATCH_SIZE]
            rate_limited = False
            for index, move in enumerate(batch):
                try:
                    move._l10n_pl_edi_submit_offline(service)
                except KSeFRateLimitError as error:
                    rate_limited = True
                    self._l10n_pl_edi_defer_offline_queue(
                        moves[index:], error, now + timedelta(seconds=error.retry_after or 3600),
                        rate_limited=True,
                    )
                except Exception as error:  # noqa: BLE001
                    self._l10n_pl_edi_defer_offline_queue(move, error, now + timedelta(hours=1))
                # KSeF may already hold the invoice: keep its state even if a later submission breaks the transaction.
                if self._can_commit():
                    self.env.cr.commit()
                if rate_limited:
                    break
            if rate_limited:
                continue
            next_send = now + timedelta(minutes=10)
            company_sudo.l10n_pl_edi_offline_next_send = next_send
            if remaining := moves - batch:
                remaining.l10n_pl_edi_offline_next_attempt = next_send
                cron._trigger(at=next_send)
