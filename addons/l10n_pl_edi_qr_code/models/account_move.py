import base64
import logging
from datetime import date, timedelta, timezone
from hashlib import sha256

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.x509.extensions import ExtensionNotFound
import dateutil.parser
from dateutil.easter import easter
from stdnum.pl.nip import compact

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date

from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError
from odoo.addons.l10n_pl_edi_qr_code.tools.ksef_api_service import (
    KsefOfflineApiService,
    KSeFTimeoutError,
)
from odoo.addons.l10n_pl_edi_qr_code.tools.ksef_latarnia_service import KsefLatarniaService


_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pl_edi_status = fields.Selection(selection_add=[
        ('offline_pending', 'Offline (Pending)'),
        ('offline_failed', 'Offline (Failed)'),
        ('offline_no_submission', 'Offline (No KSeF Submission Required)'),
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

    def _l10n_pl_edi_get_status_mapping(self):
        return super()._l10n_pl_edi_get_status_mapping() | {
            550: ('rejected', self.env._(
                "KSeF Status: Rejected (Code: 550). Processing was canceled by KSeF."
            )),
        }

    @api.model
    def _l10n_pl_edi_add_working_days(self, start_date, number):
        def get_holidays(year):
            easter_sunday = easter(year)
            holidays = {
                date(year, month, day)
                for month, day in (
                    (1, 1), (1, 6), (5, 1), (5, 3), (8, 15),
                    (11, 1), (11, 11), (12, 25), (12, 26),
                )
            } | {
                easter_sunday + timedelta(days=1),
                easter_sunday + timedelta(days=60),
            }
            if year >= 2025:
                holidays.add(date(year, 12, 24))
            return holidays

        deadline = start_date
        holiday_year = deadline.year
        holidays = get_holidays(holiday_year)
        while number:
            deadline += timedelta(days=1)
            if deadline.year != holiday_year:
                holiday_year = deadline.year
                holidays = get_holidays(holiday_year)
            if deadline.weekday() < 5 and deadline not in holidays:
                number -= 1
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

    @api.model
    def _l10n_pl_edi_get_latarnia_data(self, include_messages=False):
        service = KsefLatarniaService(self.env)
        return service.get_status(), service.get_messages() if include_messages else []

    @staticmethod
    def _l10n_pl_edi_event_overlaps_submission_period(move, event_start, event_end):
        prepared_at = move.l10n_pl_edi_offline_prepared_at or move.create_date
        return (
            prepared_at <= event_end
            and (
                not move.l10n_pl_edi_offline_deadline
                or event_start.date() <= move.l10n_pl_edi_offline_deadline
            )
        )

    def _l10n_pl_edi_apply_deadline_event(self, message, working_days, maintenance=False):
        event_start = self._l10n_pl_edi_parse_latarnia_datetime(message.get('start'))
        event_end = self._l10n_pl_edi_parse_latarnia_datetime(message.get('end'))
        if not event_start or not event_end:
            return
        event_id = str(message.get('eventId') or message.get('id'))
        deadline = self._l10n_pl_edi_add_working_days(event_end.date(), working_days)
        for move in self:
            prepared_at = move.l10n_pl_edi_offline_prepared_at or move.create_date
            event_applies = (
                event_start <= prepared_at <= event_end
                if maintenance
                else self._l10n_pl_edi_event_overlaps_submission_period(
                    move, event_start, event_end,
                )
            )
            if not event_applies:
                continue
            deadline_changed = (
                not move.l10n_pl_edi_offline_deadline
                or move.l10n_pl_edi_offline_deadline < deadline
            )
            if deadline_changed:
                move.l10n_pl_edi_offline_deadline = deadline
                move.message_post(body=self.env._(
                    "The KSeF submission deadline was adjusted to %(deadline)s based on "
                    "availability announcement %(event)s.",
                    deadline=format_date(self.env, deadline),
                    event=event_id,
                ))

    def _l10n_pl_edi_apply_total_failure(self, message, event_end=None):
        event_start = self._l10n_pl_edi_parse_latarnia_datetime(message.get('start'))
        if not event_start:
            return
        event_id = str(message.get('eventId') or message.get('id'))
        event_end = event_end or fields.Datetime.now()
        for move in self.filtered(lambda move: (
            self._l10n_pl_edi_event_overlaps_submission_period(move, event_start, event_end)
            and move.l10n_pl_edi_status != 'offline_no_submission'
        )):
            move.write({
                'l10n_pl_edi_status': 'offline_no_submission',
                'l10n_pl_edi_offline_deadline': False,
                'l10n_pl_edi_offline_next_attempt': False,
            })
            move.message_post(body=self.env._(
                "KSeF total failure announcement %(event)s removed the obligation to "
                "submit this offline invoice to KSeF.",
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
            elif message.get('category') == 'FAILURE' and message.get('type') == 'FAILURE_END':
                self._l10n_pl_edi_apply_deadline_event(message, 7)
            elif message.get('category') == 'TOTAL_FAILURE' and message.get('type') == 'FAILURE_END':
                self._l10n_pl_edi_apply_total_failure(message, event_end=event_end)

        status = (status_data or {}).get('status')
        active_message = next((
            message for message in (status_data or {}).get('messages') or []
            if message.get('category') == status
        ), {})
        if status == 'MAINTENANCE' and active_message:
            self._l10n_pl_edi_apply_deadline_event(active_message, 1, maintenance=True)
        elif status == 'TOTAL_FAILURE' and active_message:
            self._l10n_pl_edi_apply_total_failure(active_message)
        return status, active_message

    @api.model
    def _l10n_pl_edi_update_offline_cron(self):
        cron = self.env.ref('l10n_pl_edi_qr_code.cron_l10n_pl_edi_send_offline').sudo()
        has_pending = self.sudo().search_count([
            ('country_code', '=', 'PL'),
            ('l10n_pl_edi_status', 'in', ('offline_pending', 'offline_failed')),
        ], limit=1)
        if has_pending and not cron.active:
            if not self.env['ir.config_parameter'].sudo().get_param('database.is_neutralized'):
                cron.write({
                    'active': True,
                    'nextcall': fields.Datetime.now() + timedelta(minutes=cron.interval_number),
                })
        elif not has_pending and cron.active and cron.try_write({'active': False}):
            self.env['ir.cron.trigger'].sudo().search([('cron_id', '=', cron.id)]).unlink()

    def _l10n_pl_edi_generate_certificate_qr_link(self):
        self.ensure_one()
        certificate = self.company_id.sudo().l10n_pl_edi_offline_certificate
        invoice_hash = self._l10n_pl_edi_get_qr_hash()
        if not certificate or not certificate.private_key_id or not invoice_hash:
            return ''

        host = self._l10n_pl_edi_get_qr_host()
        seller_nip = compact(self.company_id.vat)
        serial = f'{int(certificate.serial_number):016X}'
        path = f'{host}/certificate/Nip/{seller_nip}/{seller_nip}/{serial}/{invoice_hash}'
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

    def action_l10n_pl_edi_prepare_offline(self):
        self.ensure_one()
        if (
            self.country_code != 'PL'
            or not self.l10n_pl_edi_register
            or self.state != 'posted'
            or self.move_type != 'out_invoice'
        ):
            raise UserError(self.env._("Only posted Polish customer invoices with KSeF enabled can be prepared offline."))
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
        status_data, messages = self._l10n_pl_edi_get_latarnia_data()
        if (status_data or {}).get('status') == 'TOTAL_FAILURE':
            raise UserError(self.env._(
                "KSeF has announced a total failure. Offline24 is not applicable and "
                "this invoice must not be queued for later KSeF submission."
            ))
        prepared_at = fields.Datetime.now()
        xml_content = self._l10n_pl_edi_render_xml().encode()
        self.write({
            'l10n_pl_edi_status': 'offline_pending',
            'l10n_pl_edi_offline_deadline': self._l10n_pl_edi_get_offline_deadline(self.invoice_date),
            'l10n_pl_edi_offline_next_attempt': prepared_at,
            'l10n_pl_edi_offline_prepared_at': prepared_at,
            'l10n_pl_edi_offline_error': False,
        })
        self._l10n_pl_edi_reconcile_latarnia(status_data, messages, prepared_at)
        self._l10n_pl_edi_store_offline_xml(xml_content)
        self._l10n_pl_edi_store_pdf()
        self.message_post(body=self.env._("The invoice was prepared in Offline24 mode and queued for KSeF."))
        self._l10n_pl_edi_update_offline_cron()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_l10n_pl_edi_cancel_offline(self):
        self.ensure_one()
        if (
            self.l10n_pl_edi_status not in ('offline_pending', 'offline_failed', 'offline_no_submission')
            or self.l10n_pl_edi_ref
            or self.l10n_pl_edi_session_id
        ):
            raise UserError(self.env._("Only an offline invoice whose KSeF submission has not started can be canceled."))
        (self.l10n_pl_edi_attachment_id | self.invoice_pdf_report_id).sudo().unlink()
        self.write(dict.fromkeys((
            'l10n_pl_edi_status',
            'l10n_pl_edi_offline_deadline',
            'l10n_pl_edi_offline_error',
            'l10n_pl_edi_offline_next_attempt',
            'l10n_pl_edi_offline_prepared_at',
        ), False))
        self.invalidate_recordset(fnames=[
            'l10n_pl_edi_attachment_id', 'l10n_pl_edi_attachment_file',
            'invoice_pdf_report_id', 'invoice_pdf_report_file',
        ])
        self.message_post(body=self.env._("The pending Offline24 submission was canceled."))
        self._l10n_pl_edi_update_offline_cron()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_l10n_pl_edi_update_invoice_status(self):
        was_accepted = self.l10n_pl_edi_status == 'accepted'
        result = super().action_l10n_pl_edi_update_invoice_status()
        if self.country_code == 'PL' and self.l10n_pl_edi_status == 'accepted' and not was_accepted:
            try:
                self._l10n_pl_edi_store_pdf()
            except Exception:  # noqa: BLE001
                self.message_post(body=self.env._("The KSeF invoice was accepted, but its PDF visualization could not be generated."))
        return result

    @api.depends('l10n_pl_edi_status')
    def _compute_show_reset_to_draft_button(self):
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda move: move.l10n_pl_edi_status in (
            'offline_pending', 'offline_failed', 'offline_no_submission'
        )).show_reset_to_draft_button = False

    @api.model
    def _l10n_pl_edi_defer_offline_queue(self, moves, error, retry_at, rate_limited=False):
        move = moves[0]
        first_failure = move.l10n_pl_edi_status != 'offline_failed'
        move.write({
            'l10n_pl_edi_status': 'offline_failed',
            'l10n_pl_edi_offline_error': str(error),
        })
        moves.l10n_pl_edi_offline_next_attempt = retry_at
        move.company_id.sudo().l10n_pl_edi_offline_next_send = retry_at
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
        if status == 'accepted':
            try:
                self._l10n_pl_edi_store_pdf()
            except Exception:  # noqa: BLE001
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
            response = service.send_offline_invoice(xml_content)
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

    @api.model
    def _cron_l10n_pl_edi_send_offline(self):
        now = fields.Datetime.now()
        cron = self.env.ref('l10n_pl_edi_qr_code.cron_l10n_pl_edi_send_offline')
        queue_domain = [
            ('country_code', '=', 'PL'),
            ('l10n_pl_edi_status', 'in', ('offline_pending', 'offline_failed')),
        ]
        queue_order = 'l10n_pl_edi_offline_deadline ASC NULLS LAST, invoice_date, id'
        queued = self.search(queue_domain, order=queue_order)
        if not queued:
            self._l10n_pl_edi_update_offline_cron()
            return

        status_data, messages = self._l10n_pl_edi_get_latarnia_data(include_messages=True)
        latarnia_status, active_message = queued._l10n_pl_edi_reconcile_latarnia(
            status_data, messages, now,
        )
        if latarnia_status in ('MAINTENANCE', 'FAILURE', 'TOTAL_FAILURE'):
            queued = queued.filtered_domain(queue_domain)
            if queued:
                event_end = self._l10n_pl_edi_parse_latarnia_datetime(active_message.get('end'))
                retry_at = event_end or now + timedelta(minutes=cron.interval_number)
                queued.l10n_pl_edi_offline_next_attempt = retry_at
                cron._trigger(at=retry_at)
            self._l10n_pl_edi_update_offline_cron()
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
            move = moves[0]
            service = KsefOfflineApiService(company)
            try:
                move._l10n_pl_edi_submit_offline(service)
            except Exception as error:  # noqa: BLE001
                rate_limited = isinstance(error, KSeFRateLimitError)
                retry_delay = error.retry_after if rate_limited else None
                self._l10n_pl_edi_defer_offline_queue(
                    moves, error, now + timedelta(seconds=retry_delay or 3600),
                    rate_limited=rate_limited,
                )
            else:
                next_send = now + timedelta(minutes=1)
                company_sudo.l10n_pl_edi_offline_next_send = next_send
                if remaining := moves - move:
                    remaining.l10n_pl_edi_offline_next_attempt = next_send
                    cron._trigger(at=next_send)
        self._l10n_pl_edi_update_offline_cron()

    def _l10n_pl_edi_get_qr_host(self):
        mode = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_pl_edi_ksef.mode', 'prod'
        )
        return f"qr{'' if mode == 'prod' else '-test'}.ksef.mf.gov.pl"

    def _l10n_pl_edi_get_qr_hash(self):
        self.ensure_one()
        xml_content = self._l10n_pl_edi_get_xml_bytes()
        return base64.urlsafe_b64encode(
            sha256(xml_content).digest()
        ).decode().rstrip('=') if xml_content else ''

    def _l10n_pl_edi_get_xml_bytes(self):
        self.ensure_one()
        if self.l10n_pl_edi_attachment_file:
            return base64.b64decode(self.l10n_pl_edi_attachment_file)
        attachment = self.l10n_pl_edi_attachment_id
        return attachment.raw if attachment else b''

    def _l10n_pl_edi_generate_qr_link(self):
        self.ensure_one()
        if self.country_code != 'PL':
            return ''
        invoice_hash = self._l10n_pl_edi_get_qr_hash()
        seller_vat = self.company_id.vat if self.is_sale_document() else self.commercial_partner_id.vat
        if not invoice_hash or not seller_vat or not self.invoice_date:
            return ''
        host = self._l10n_pl_edi_get_qr_host()
        return f"https://{host}/invoice/{compact(seller_vat)}/{self.invoice_date:%d-%m-%Y}/{invoice_hash}"

    def _l10n_pl_edi_store_pdf(self):
        self.ensure_one()
        old_pdf = self.invoice_pdf_report_id
        content = self.env['ir.actions.report'].with_company(self.company_id)._render_qweb_pdf(
            'account.account_invoices', res_ids=self.ids,
        )[0]
        self.env['ir.attachment'].sudo().create({
            'name': self._get_invoice_report_filename(),
            'raw': content,
            'mimetype': 'application/pdf',
            'res_model': self._name,
            'res_id': self.id,
            'res_field': 'invoice_pdf_report_file',
        })
        old_pdf.unlink()
        self.invalidate_recordset(fnames=['invoice_pdf_report_id', 'invoice_pdf_report_file'])

    def _fetch_bills_data(self, service, bills_to_fetch):
        blocking_error = super()._fetch_bills_data(service, bills_to_fetch)
        for bill in bills_to_fetch.filtered(
            lambda move: move.country_code == 'PL' and move.l10n_pl_edi_status == 'fetched'
        ):
            try:
                bill._l10n_pl_edi_store_pdf()
            except Exception:  # noqa: BLE001
                _logger.exception("Could not render the KSeF bill visualization for %s", bill.display_name)
                bill.message_post(body=self.env._(
                    "The KSeF XML was imported, but its PDF visualization could not be generated."
                ))
        return blocking_error
