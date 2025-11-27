import base64
import calendar
import io
import logging
import re
import uuid
import zipfile
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from .pdp_payload import PdpPayloadBuilder
from ..utils.vat import is_valid_vat

_logger = logging.getLogger(__name__)


class PdpFlow(models.Model):
    _name = 'l10n.fr.pdp.flow'
    _description = 'French PDP Flow'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # -------------------------------------------------------------------------
    # Default Methods (before fields per Odoo guidelines)
    # -------------------------------------------------------------------------

    def _default_name(self):
        return _("Flow %(date)s", date=fields.Date.context_today(self))

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    name = fields.Char(string="Reference", required=True, copy=False, default=_default_name)
    reporting_date = fields.Date(
        string="Reporting Date",
        required=True,
        help="Date associated with the aggregated reporting period.",
        index=True,
    )
    flow_type = fields.Char(
        string="Flux Type",
        default='transaction_report',
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('building', "Building"),
            ('ready', "Ready"),
            ('pending', "Sent"),
            ('done', "Completed"),
            ('error', "Error"),
        ],
        string="Status",
        required=True,
        default='draft',
        index=True,
    )
    payload = fields.Binary(string="Payload", attachment=True, help="XML payload sent to the PDP API.")
    payload_filename = fields.Char(string="Payload Filename")
    payload_sha256 = fields.Char(string="Payload SHA-256", help="Checksum of the generated payload.", copy=False)
    transport_identifier = fields.Char(string="Transport Identifier", help="Identifier returned by the PDP transport API.")
    transport_status = fields.Char(string="Transport Status", help="Raw status returned by the PDP transport API.")
    transport_message = fields.Text(string="Transport Message", help="Additional message or error returned by the PDP transport API.")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        help="Currency of the aggregated transactions included in the payload.",
    )
    document_type = fields.Selection(
        selection=[('sale', "Sale"), ('refund', "Refund"), ('mixed', "Mixed")],
        string="Document Type",
        default='sale',
        required=True,
    )
    report_kind = fields.Selection(
        selection=[('transaction', "Transaction Report"), ('payment', "Payment Report")],
        string="Report Kind",
        required=True,
        default='transaction',
        index=True,
    )
    transaction_type = fields.Selection(
        selection=[('b2c', "B2C Domestic"), ('international', "International B2B"), ('mixed', "Mixed Scope")],
        string="Transaction Scope",
        default='b2c',
        required=True,
        index=True,
    )
    transmission_type = fields.Selection(
        selection=[('IN', "Initial"), ('CO', "Complementary"), ('MO', "Corrective"), ('RE', "Rectificative")],
        string="Transmission Type",
        required=True,
        default='IN',
    )
    transmission_reference = fields.Char(string="Previous Transmission ID", copy=False)
    transmission_reference_type = fields.Selection(
        selection=[('IN', "Initial"), ('CO', "Complementary"), ('MO', "Corrective"), ('RE', "Rectificative")],
        string="Previous Transmission Type",
        copy=False,
    )
    issue_datetime = fields.Datetime(
        string="Issue Datetime",
        default=fields.Datetime.now,
        help="Timestamp at which the transmission is generated (TT-3).",
        copy=False,
    )
    tracking_id = fields.Char(string="Tracking Identifier", help="External tracking identifier sent to the Flow Service.", copy=False)
    has_payload = fields.Boolean(string="Has Payload", compute="_compute_has_payload", readonly=True)
    slice_ids = fields.One2many(
        comodel_name="l10n.fr.pdp.flow.slice",
        inverse_name="flow_id",
        string="Slices",
        copy=False,
    )
    flow_profile = fields.Char(string="Flow Profile", default='Extended-CTC-FR', readonly=True)
    flow_direction = fields.Char(string="Flow Direction", default='Out', readonly=True)
    revision = fields.Integer(string="Revision", default=0, copy=False)
    period_start = fields.Date(string="Period Start", copy=False)
    period_end = fields.Date(string="Period End", copy=False)
    periodicity_code = fields.Char(string="Periodicity Code", copy=False)
    is_correction = fields.Boolean(string="Correction Flow", copy=False)
    last_send_datetime = fields.Datetime(string="Last Send On")
    send_datetime = fields.Datetime(string="Sent On", copy=False)
    attempt_count = fields.Integer(string="Send Attempts", default=0)
    acknowledgement_status = fields.Selection(
        selection=[('pending', "Pending"), ('ok', "Accepted"), ('error', "Error")],
        string="Last Known Status",
        default='pending',
        copy=False,
    )
    acknowledgement_details = fields.Json(string="Acknowledgement Details", copy=False)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="l10n_fr_pdp_flow_move_rel",
        column1="flow_id",
        column2="move_id",
        string="Source Moves",
        help="Invoices that produced this flow.",
    )
    payment_move_count = fields.Integer(string="Payments", compute="_compute_payment_move_count")
    error_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="l10n_fr_pdp_flow_error_move_rel",
        column1="flow_id",
        column2="move_id",
        string="Invalid Invoices",
        help="Invoices excluded from the payload because of validation errors.",
        copy=False,
    )
    error_move_message = fields.Text(string="Invalid Invoice Details", copy=False)
    company_periodicity = fields.Selection(
        related="company_id.l10n_fr_pdp_periodicity",
        string="Transaction Periodicity",
        readonly=True,
    )
    company_payment_periodicity = fields.Selection(
        related="company_id.l10n_fr_pdp_payment_periodicity",
        string="Payment Periodicity",
        readonly=True,
    )
    next_deadline_start = fields.Date(string="Next Send Window Start", compute="_compute_deadline_preview", store=True)
    next_deadline_end = fields.Date(string="Next Send Window End", compute="_compute_deadline_preview", store=True)

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends("slice_ids.payload")
    def _compute_has_payload(self):
        for flow in self:
            flow.has_payload = any(s.payload for s in flow.slice_ids)

    @api.depends(
        "period_start",
        "period_end",
        "report_kind",
        "company_id.l10n_fr_pdp_periodicity",
        "company_id.l10n_fr_pdp_payment_periodicity",
        "company_id.l10n_fr_pdp_deadline_override_start",
        "company_id.l10n_fr_pdp_deadline_override_end",
    )
    def _compute_deadline_preview(self):
        today = fields.Date.context_today(self)
        for flow in self:
            window = flow._compute_deadline_window(today)
            flow.next_deadline_start = window[0] if window else False
            flow.next_deadline_end = window[1] if window else False

    def _compute_payment_move_count(self):
        for flow in self:
            flow.payment_move_count = len(flow._get_payment_entries())

    # -------------------------------------------------------------------------
    # CRUD Methods
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if reporting_date := vals.get("reporting_date"):
                vals.setdefault("period_start", reporting_date)
                vals.setdefault("period_end", reporting_date)
        records = super().create(vals_list)
        records._update_reference_name()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "reporting_date" in vals and "period_start" not in vals and "period_end" not in vals:
            for flow in self:
                flow.period_start = flow.period_start or flow.reporting_date
                flow.period_end = flow.period_end or flow.reporting_date
        return res

    # -------------------------------------------------------------------------
    # Business Methods - Validation
    # -------------------------------------------------------------------------

    def _filter_valid_moves(self, moves, invalid_collector=None, log_event=False):
        """Separate valid moves from invalid ones, updating error tracking."""
        self.ensure_one()
        invalid_moves = {
            move.id: errors
            for move in moves
            if (errors := self._get_move_validation_errors(move))
        }
        valid_moves = moves.filtered(lambda m: m.id not in invalid_moves)
        if invalid_moves:
            if invalid_collector is not None:
                invalid_collector.update(invalid_moves)
            else:
                self._update_error_moves(invalid_moves, log_event=log_event)
        else:
            if invalid_collector is None:
                self._clear_error_moves()
        return valid_moves, invalid_moves

    def _get_move_validation_errors(self, move):
        """Return list of validation errors for a move, empty if valid."""
        errors = []
        if move.state == "posted" and move.is_sale_document(include_receipts=True) and not move.is_move_sent:
            errors.append(_("Invoice/credit note has not been sent to the customer."))
        if move._get_l10n_fr_pdp_transaction_type() == "international":
            partner = move.commercial_partner_id
            vat = partner.vat
            country_code = partner.country_id.code if partner.country_id else None
            if not vat:
                errors.append(_("Missing buyer VAT."))
            elif not is_valid_vat(vat, country_code):
                errors.append(_("Invalid buyer VAT (%(vat)s).", vat=vat))
        return errors

    def _update_error_moves(self, invalid_moves, log_event=False):
        self.ensure_one()
        invalid_ids = list(invalid_moves.keys())
        # Avoid spamming chatter if the same invalid set was already recorded.
        if set(invalid_ids) == set(self.error_move_ids.ids) and self.error_move_message:
            return
        self.error_move_ids = [Command.set(invalid_ids)]
        details = []
        for move_id, reasons in invalid_moves.items():
            move = self.env["account.move"].browse(move_id)
            details.append("%s: %s" % (move.display_name, "; ".join(reasons)))
            # Only post on the move if the content differs to limit spam.
            errors_html = Markup("<br/>").join(reasons)
            body = Markup(_("Excluded from PDP flow %s due to validation errors:", self.display_name)) + Markup("<br/>") + errors_html
            last_body = move.message_ids[:1].body if move.message_ids else None
            if last_body != body:
                move.message_post(body=body, subtype_xmlid="mail.mt_note")
        self.error_move_message = "\n".join(details)
        if log_event:
            self._log_cron_event(
                _("Flow contains %(count)s invalid invoice(s) that were excluded.", count=len(invalid_ids)),
            )

    def _clear_error_moves(self):
        self.error_move_ids = [Command.clear()]
        self.error_move_message = False

    # -------------------------------------------------------------------------
    # Business Methods - Payload Building
    # -------------------------------------------------------------------------

    def _build_payload(self):
        """Build XML payload for all slices in the flow."""
        open_states = {'draft', 'building', 'ready', 'error'}
        for flow in self:
            if flow.state not in open_states:
                raise UserError(_("Flow %(name)s has already been sent.", name=flow.name))
            flow._ensure_tracking_id()
            flow.state = 'building'
            if not flow.slice_ids:
                flow._reset_slices(flow.move_ids)
            invalid_acc = {}
            builder = PdpPayloadBuilder(flow)
            new_revision = (flow.revision or 0) + 1
            for slice_rec in flow.slice_ids:
                valid_moves, invalids = flow._filter_valid_moves(
                    slice_rec.move_ids, invalid_collector=invalid_acc, log_event=True,
                )
                slice_rec.invalid_move_ids = [Command.set(list(invalids.keys()))] if invalids else [Command.clear()]
                if not valid_moves:
                    slice_rec.write({
                        **self._payload_reset(),
                        'state': 'error',
                        'transport_status': 'ERROR',
                        'transport_message': _("No valid invoices for this slice."),
                    })
                    continue
                build_result = builder.build(valid_moves, slice_rec.slice_date, invalid_acc)
                slice_rec.write({
                    'payload': build_result['payload'],
                    'payload_filename': build_result['filename'],
                    'payload_sha256': build_result.get('sha256'),
                    'state': 'ready',
                })
            slice_states = flow.slice_ids.mapped('state')
            ready_slices = sum(1 for s in slice_states if s == 'ready')
            error_slices = sum(1 for s in slice_states if s == 'error')
            if invalid_acc:
                flow._update_error_moves(invalid_acc)
            else:
                flow._clear_error_moves()
            if error_slices or invalid_acc:
                flow.state = 'error'
            elif 'pending' in slice_states:
                flow.state = 'pending'
            elif 'done' in slice_states:
                flow.state = 'done'
            elif ready_slices:
                flow.state = 'ready'
            else:
                flow.state = 'draft'
            flow._message_post_once(_(
                "Payload build completed: %(ready)s ready slice(s), %(error)s error slice(s).",
                ready=ready_slices,
                error=error_slices,
            ))
            flow.revision = new_revision
            flow.write({
                **self._payload_reset(),
                'acknowledgement_status': 'pending',
                'acknowledgement_details': False,
                'issue_datetime': fields.Datetime.now(),
            })

    def _payload_reset(self):
        """Return dict to clear payload-related fields."""
        return {'payload': False, 'payload_filename': False, 'payload_sha256': False}

    # -------------------------------------------------------------------------
    # Business Methods - Sending
    # -------------------------------------------------------------------------

    def action_send(self):
        """Send flow slices to transport gateway."""
        for flow in self:
            flow._ensure_tracking_id()
            if flow.state not in {'ready', 'error'} and not flow.slice_ids:
                flow._build_payload()
            send_logs = []
            for slice_rec in flow.slice_ids.filtered(lambda s: s.state == 'ready'):
                response = flow._send_to_transport(slice_rec)
                status = flow._map_transport_status(response)
                send_datetime = fields.Datetime.now()
                slice_rec.write({
                    'transport_identifier': response.get('id'),
                    'transport_status': response.get('status'),
                    'transport_message': response.get('message'),
                    'state': status,
                })
                flow.last_send_datetime = send_datetime
                if status in {'pending', 'done'}:
                    flow.send_datetime = send_datetime
                    flow.issue_datetime = send_datetime
                flow.acknowledgement_status = 'ok' if status == 'done' else ('error' if status == 'error' else 'pending')
                flow.acknowledgement_details = response.get('acknowledgement')
                slice_rec.aggregate_state_to_flow()
                if flow.error_move_ids and self.env.context.get('ignore_error_invoices'):
                    flow._schedule_correction_for_error_moves()
                flow.transport_identifier = response.get('id') or flow.transport_identifier
                flow.transport_status = response.get('status') or flow.transport_status
                flow.transport_message = response.get('message') or flow.transport_message
                if status in {'pending', 'done'}:
                    flow._post_sent_message_on_moves(slice_rec)
                send_logs.append({
                    'date': fields.Date.to_string(slice_rec.slice_date),
                    'doc': slice_rec.document_type,
                    'status': status,
                    'transport': response.get('id') or _("n/a"),
                    'details': response.get('message') or "",
                })
            if send_logs:
                log_lines = [
                    _("Slice %(date)s (doc: %(doc)s): status %(status)s, transport %(transport)s. %(details)s",
                      date=log['date'], doc=log['doc'], status=log['status'], transport=log['transport'], details=log['details'])
                    for log in send_logs
                ]
                flow._message_post_once("<br/>".join(log_lines))
            # When sending while ignoring invalid invoices, mark remaining error slices as done
            # to reflect that the valid content was dispatched and the correction flow handles the rest.
            if self.env.context.get('ignore_error_invoices') and flow.slice_ids.filtered(lambda s: s.state == 'error'):
                flow.slice_ids.filtered(lambda s: s.state == 'error').write({
                    'state': 'done',
                    'transport_status': 'IGNORED',
                    'transport_message': _("Ignored invalid invoices (handled via correction flow)."),
                })
                flow.slice_ids[:1].aggregate_state_to_flow()

    def _post_sent_message_on_moves(self, slice_rec):
        """Post audit message on successfully sent moves."""
        sent_moves = slice_rec.move_ids - slice_rec.invalid_move_ids
        if not sent_moves:
            return
        flow_link = Markup('<a href="#id=%s&amp;model=l10n.fr.pdp.flow">%s</a>') % (self.id, _("See details"))
        body = Markup("Sent in e-reporting. %s") % flow_link
        for move in sent_moves:
            move.message_post(body=body, subtype_xmlid="mail.mt_note")

    def _send_to_transport(self, slice_rec=None):
        """Prepare and send request to transport gateway."""
        return self._call_transport_gateway(self._prepare_transport_request(slice_rec))

    def _call_transport_gateway(self, request_payload):
        """Mock transport gateway - replace with real IAP integration."""
        return {
            'id': str(uuid.uuid4()),
            'status': 'ACCEPTED',
            'message': "Mock transport gateway response",
            'acknowledgement': [{'level': 'info', 'item': 'flow', 'reason': _("Mock acknowledgement")}],
            'request': request_payload,
        }

    def _map_transport_status(self, response):
        """Map API status to internal state."""
        raw_status = (response or {}).get('status', '').upper()
        mapping = {
            'ACCEPTED': 'done',
            'DELIVERED': 'done',
            'ERROR': 'error',
            'REFUSED': 'error',
        }
        return mapping.get(raw_status, 'pending')

    def _prepare_transport_request(self, slice_rec=None):
        """Build request payload for transport API."""
        self.ensure_one()
        self._ensure_tracking_id()
        target_payload = slice_rec.payload if slice_rec else self.payload
        target_sha = slice_rec.payload_sha256 if slice_rec else self.payload_sha256
        target_filename = slice_rec.payload_filename if slice_rec else self.payload_filename
        company = self.company_id
        partner = company.partner_id
        company_siret = (
            company.l10n_fr_siret if 'l10n_fr_siret' in company._fields else ''
        ) or company.siret or (
            partner.l10n_fr_siret if 'l10n_fr_siret' in partner._fields else ''
        ) or ''
        flow_type = 'TransactionReport'
        if self.report_kind == 'transaction':
            flow_type = 'AggregatedCustomerTransactionReport' if self.transaction_type == 'b2c' else 'IndividualCustomerTransactionReport'
        else:
            flow_type = 'AggregatedCustomerPaymentReport' if self.transaction_type == 'b2c' else 'UnitaryCustomerPaymentReport'
        return {
            'flowType': flow_type,
            'flowSyntax': 'FRR',  # FRR = Flux 10 reporting syntax
            'flowProfile': self.flow_profile,
            'flowDirection': self.flow_direction,
            'trackingId': self.tracking_id,
            'companySiret': company_siret,
            'documentType': self.document_type,
            'transactionType': self.transaction_type,
            'transmissionType': self.transmission_type,
            'transmissionReference': self.transmission_reference,
            'transmissionReferenceType': self.transmission_reference_type,
            'issueDateTime': fields.Datetime.to_string(self.issue_datetime) if self.issue_datetime else False,
            'periodStart': self._format_date(self.period_start),
            'periodEnd': self._format_date(self.period_end),
            'reportingDate': self._format_date(self.reporting_date),
            'periodicity': self.periodicity_code,
            'payload': target_payload,
            'filename': target_filename,
            'sha256': target_sha,
            'attachmentNumber': 1 if target_payload else 0,
        }

    # -------------------------------------------------------------------------
    # Business Methods - Cron
    # -------------------------------------------------------------------------

    @api.model
    def _cron_send_ready_flows(self):
        """Cron job to send ready flows within their send window."""
        today = fields.Date.context_today(self)
        companies = self.env["res.company"].search([
            ("l10n_fr_pdp_enabled", "=", True),
            ("l10n_fr_pdp_send_mode", "=", "auto"),
        ])
        if not companies:
            return True
        flows = self.search([("state", "in", ('ready', 'error')), ("company_id", "in", companies.ids)])
        for flow in flows:
            try:
                # IN waits strictly for its window; CO/RE/MO send immediately when ready.
                if flow.transmission_type == 'IN':
                    window = flow._compute_deadline_window(today)
                    if not window:
                        continue
                    start, end = window
                    if today < start or today > end:
                        continue
                    # Only ignore errors on the last day of the window
                    ctx = {} if (not flow.error_move_ids or today < end) else {'ignore_error_invoices': True}
                else:
                    ctx = {'ignore_error_invoices': bool(flow.error_move_ids)}
                flow.with_context(**ctx).with_company(flow.company_id).sudo().action_send()
                flow._log_cron_event(
                    _("Flow automatically sent by cron (status: %(status)s). %(extra)s",
                      status=flow.transport_status or flow.state,
                      extra=_("Invalid invoices were excluded.") if flow.error_move_ids else ""),
                )
            except Exception:
                _logger.exception("Failed to send PDP flow %s during cron", flow.id)
        return True

    def _schedule_correction_for_error_moves(self):
        """Create a correction flow for error moves after successful send."""
        self.ensure_one()
        if not self.error_move_ids:
            return
        new_flow = self.copy({
            'name': self._default_name(),
            'state': 'draft',
            **self._payload_reset(),
            'acknowledgement_status': 'pending',
            'acknowledgement_details': False,
            'last_send_datetime': False,
            'send_datetime': False,
            'transmission_type': 'CO',
            'transmission_reference': self.transmission_reference or self.transport_identifier or False,
            'transmission_reference_type': self.transmission_reference_type or self.transmission_type or False,
            'is_correction': False,
            'move_ids': [Command.set(self.error_move_ids.ids)],
            'error_move_ids': [Command.clear()],
            'error_move_message': False,
        })
        new_flow._update_reference_name()
        self._clear_error_moves()
        flow_link = Markup('<a href="#id=%s&amp;model=l10n.fr.pdp.flow">%s</a>') % (new_flow.id, new_flow.display_name)
        self._log_cron_event(
            Markup(_("Correction flow %(flow)s created for %(count)s invalid invoice(s).",
                    flow=flow_link,
                    count=len(new_flow.move_ids))),
        )

    # -------------------------------------------------------------------------
    # Business Methods - Deadline Window
    # -------------------------------------------------------------------------

    def _compute_deadline_window(self, today):
        """Compute send window dates for the flow."""
        self.ensure_one()
        company = self.company_id
        override_start = company.l10n_fr_pdp_deadline_override_start
        override_end = company.l10n_fr_pdp_deadline_override_end
        if override_start and override_end:
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            start_day = min(max(1, override_start), days_in_month)
            end_day = min(max(start_day, override_end), days_in_month)
            return today.replace(day=start_day), today.replace(day=end_day)

        period_end = fields.Date.to_date(self.period_end or self.reporting_date)
        if not period_end:
            return False
        periodicity = company.l10n_fr_pdp_payment_periodicity if self.report_kind == 'payment' else company.l10n_fr_pdp_periodicity
        periodicity = periodicity or ('monthly' if self.report_kind == 'payment' else 'decade')

        def _one_day(date_val):
            return date_val, date_val

        if periodicity == 'bimonthly':
            # Official rule: bimonthly send window is 25-30 of following month (AFNOR/PPF guideline)
            anchor = period_end + relativedelta(months=1)
            last_day = calendar.monthrange(anchor.year, anchor.month)[1]
            start_day = min(25, last_day)
            end_day = min(30, last_day)
            return anchor.replace(day=start_day), anchor.replace(day=end_day)

        if periodicity == 'monthly':
            # Monthly: due on the 10th of the following month (or last day if shorter month)
            anchor = (period_end + relativedelta(months=1)).replace(day=1)
            last_day = calendar.monthrange(anchor.year, anchor.month)[1]
            send_day = min(10, last_day)
            return _one_day(anchor.replace(day=send_day))

        # Decade (default)
        day = period_end.day
        last_day = calendar.monthrange(period_end.year, period_end.month)[1]
        if day <= 10:
            # Decade 1-10 -> due on the 20th
            send_date = period_end.replace(day=min(20, last_day))
            return _one_day(send_date)
        if day <= 20:
            # Decade 11-20 -> due on month end
            send_date = period_end.replace(day=last_day)
            return _one_day(send_date)
        # Decade 21+ -> due on the 10th of next month
        send_date = (period_end + relativedelta(months=1)).replace(day=10)
        return _one_day(send_date)

    def _is_within_send_window(self, today=None):
        """Check if today is within the flow's send window."""
        self.ensure_one()
        today = today or fields.Date.context_today(self)
        window = self._compute_deadline_window(today)
        if not window:
            return False
        return window[0] <= today <= window[1]

    def _is_last_send_day(self, today=None):
        """Check if today is the last day of the send window."""
        today = today or fields.Date.context_today(self)
        window = self._compute_deadline_window(today)
        return window and today >= window[1]

    # -------------------------------------------------------------------------
    # Business Methods - Slice Management
    # -------------------------------------------------------------------------

    def _reset_slices(self, moves):
        """Recreate slices based on move dates and document types."""
        self.ensure_one()
        refund_types = [mt for mt in self.env["account.move"].get_sale_types(include_receipts=True) if 'refund' in mt]
        grouped = {}
        for move in moves:
            move_date = move.invoice_date or move.date
            doc_type = 'refund' if move.move_type in refund_types else 'sale'
            key = (move_date, doc_type)
            grouped.setdefault(key, self.env["account.move"].browse())
            grouped[key] |= move

        existing = {(s.slice_date, s.document_type): s for s in self.slice_ids}
        seen = set()
        for (slice_date, doc_type), slice_moves in grouped.items():
            seen.add((slice_date, doc_type))
            vals = {
                'slice_date': slice_date,
                'document_type': doc_type,
                'move_ids': [Command.set(slice_moves.ids)],
                'invalid_move_ids': [Command.clear()],
                'state': 'draft',
                **self._payload_reset(),
                'transport_identifier': False,
                'transport_status': False,
                'transport_message': False,
            }
            if slice_rec := existing.get((slice_date, doc_type)):
                slice_rec.write(vals)
            else:
                vals['flow_id'] = self.id
                self.env["l10n.fr.pdp.flow.slice"].create(vals)
        unused = [s for key, s in existing.items() if key not in seen]
        if unused:
            self.env["l10n.fr.pdp.flow.slice"].browse([s.id for s in unused]).unlink()

    def _synchronize_moves(self, moves):
        """Update flow's moves, resetting payload if changed."""
        self.ensure_one()
        if self.move_ids == moves:
            return False
        values = {
            'move_ids': [Command.set(moves.ids)],
            **self._payload_reset(),
        }
        if self.state not in {'draft', 'error'}:
            values['state'] = 'draft'
        self.write(values)
        self._reset_slices(moves)
        return True

    # -------------------------------------------------------------------------
    # Business Methods - Tracking & Naming
    # -------------------------------------------------------------------------

    def _ensure_tracking_id(self):
        """Generate or normalize tracking ID."""
        for flow in self:
            if flow.tracking_id:
                normalized = flow._sanitize_token(flow.tracking_id, default='TRACKING').upper()
                if normalized != flow.tracking_id:
                    flow.tracking_id = normalized
            else:
                flow.tracking_id = flow._generate_tracking_id()

    def _generate_tracking_id(self):
        """Generate unique tracking ID from company and flow attributes."""
        self.ensure_one()
        company = self.company_id
        siren = (company.siret or '')[:9]
        reporting_token = self._format_date(self.reporting_date) if self.reporting_date else fields.Date.context_today(self)
        parts = [siren or str(company.id), (self.report_kind or '')[:8], (self.transaction_type or '')[:8], str(reporting_token)]
        return self._sanitize_token("_".join(p for p in parts if p), default='TRACKING').upper()

    def _sanitize_token(self, value, default='FLOW'):
        """Clean token for use in filenames and identifiers."""
        value = (value or '').strip()
        if not value:
            return default
        # remove non-alphanumeric characters
        return re.sub(r'[^A-Za-z0-9_-]+', '_', value)[:50] or default

    def _update_reference_name(self):
        """Set human-readable flow name based on period."""
        for flow in self:
            date_ref = flow.period_start or flow.reporting_date
            if not date_ref:
                continue
            date_ref = fields.Date.to_date(date_ref)
            base = _("E-reporting %(month)s/%(year)s", month=date_ref.strftime("%m"), year=date_ref.strftime("%Y"))
            if flow.periodicity_code == 'D':
                day = date_ref.day
                part = 1 if day <= 10 else (2 if day <= 20 else 3)
                base = _("%(base)s Decade Part %(part)s/3", base=base, part=part)
            flow.name = base

    def _build_filename(self, revision=None, extension='xml'):
        """Generate unique filename for payload."""
        self.ensure_one()
        self._ensure_tracking_id()
        profile_token = self._sanitize_token(self.flow_profile or 'FRR', default='FRR').upper()
        base_token = self._sanitize_token(self.tracking_id, default='TRACKING').upper()
        suffix = revision if revision is not None else self.revision
        if suffix:
            return f"{profile_token}_{base_token}_r{suffix}.{extension}"
        return f"{profile_token}_{base_token}.{extension}"

    # -------------------------------------------------------------------------
    # Business Methods - Utilities
    # -------------------------------------------------------------------------

    def _format_date(self, value):
        """Format date as YYYYMMDD string."""
        if not value:
            return ''
        if isinstance(value, str):
            value = fields.Date.from_string(value)
        return value.strftime('%Y%m%d')

    def _format_amount(self, amount):
        """Round amount to currency precision."""
        currency = self.currency_id or self.env.company.currency_id
        return currency.round(amount) if currency else amount

    def _message_post_once(self, body, subtype="mail.mt_note"):
        """Post message if it differs from the last one to avoid chatter spam."""
        self.ensure_one()
        last_body = self.message_ids[:1].body if self.message_ids else None
        if last_body == body:
            return
        self.message_post(body=body, subtype_xmlid=subtype)

    def _is_valid_vat(self, vat, country_code=None):
        """Validate VAT number using stdnum."""
        return bool(vat) and is_valid_vat(vat, country_code)

    def _is_valid_due_date_code(self, code):
        """Validate TT-64 due date type code."""
        return bool(code and code.isdigit() and len(code) <= 3)

    def _get_transaction_category_code(self, transaction_type):
        """Return category code for transaction type."""
        return 'TPS1' if transaction_type == 'international' else 'TLB1'  # Flux 10 category codes: TPS1=international, TLB1=B2C

    def _log_cron_event(self, message):
        """Post message to flow chatter."""
        for flow in self:
            flow._message_post_once(message)

    def _mark_as_outdated(self):
        """Reset flow to draft state when source data changes."""
        for flow in self:
            flow.write({
                'state': 'draft',
                **flow._payload_reset(),
                'acknowledgement_status': 'pending',
                'acknowledgement_details': False,
                'issue_datetime': fields.Datetime.now(),
                'revision': (flow.revision or 0) + 1,
            })

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_build_payload_manual(self):
        """Manual trigger for payload building."""
        self._ensure_tracking_id()
        self._build_payload()
        _logger.info("Manual payload build triggered for flows: %s", self.ids)
        return True

    def action_send_from_ui(self):
        """Send flow from UI with error checking."""
        self._ensure_tracking_id()
        ctx = dict(self.env.context)
        for flow in self:
            if flow.error_move_ids and not (ctx.get('ignore_error_invoices') or flow._is_last_send_day()):
                raise UserError(_(
                    "This flow still contains invoices with validation errors. "
                    "Fix them or use the 'Send without invalid invoices' button.",
                ))
        _logger.info("Manual transport submission triggered for flows: %s", self.ids)
        return self.with_context(ctx).action_send()

    def action_send_ignore_errors(self):
        """Send flow ignoring error invoices."""
        return self.with_context(ignore_error_invoices=True).action_send_from_ui()

    def action_download_payload(self):
        """Download flow payload(s) as file or zip."""
        self.ensure_one()
        slices = self.slice_ids.filtered(lambda s: s.payload)
        if not slices:
            raise UserError(_("This flow has no payload yet. Build it before downloading."))
        if len(slices) == 1:
            slice_rec = slices[0]
            filename = slice_rec.payload_filename or self._build_filename()
            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/content/{slice_rec._name}/{slice_rec.id}/payload?download=true&filename={filename}",
                'target': 'self',
            }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:  # nosec: in-memory zip for download
            for slice_rec in slices:
                data = base64.b64decode(slice_rec.payload)
                filename = slice_rec.payload_filename or self._build_filename()
                archive.writestr(filename, data)
        attachment = self.env['ir.attachment'].create({
            'name': f"{self.name or 'flow'}.zip",
            'datas': base64.b64encode(buffer.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/zip',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=true",
            'target': 'self',
        }

    def action_view_error_moves(self):
        """Open list view of invalid invoices."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Invalid Invoices"),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.error_move_ids.ids)],
        }

    def action_open_send_wizard(self):
        """Open send wizard if errors exist, otherwise send directly."""
        self.ensure_one()
        if not self.error_move_ids:
            return self.action_send_from_ui()
        view = self.env.ref("l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_send_wizard_form", raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n.fr.pdp.send.wizard',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'target': 'new',
            'context': {'default_flow_id': self.id},
        }

    def action_view_moves(self):
        """Open list view of related invoices."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.move_ids.ids)],
            'name': _("Related Invoices"),
            'context': {'create': False, 'group_by': ['move_type']},
        }

    def _get_payment_entries(self):
        """Return payment/bank moves linked to this flow's invoices."""
        payments = self.env["account.move"].browse()
        for move in self.move_ids:
            if move.move_type == "out_receipt":
                payments |= move
            for partial in move._get_all_reconciled_invoice_partials():
                aml = partial.get("aml")
                if aml:
                    payments |= aml.move_id
        return payments

    def action_view_payments(self):
        """Open list view of related payment entries."""
        self.ensure_one()
        payments = self._get_payment_entries()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payments.ids)],
            'name': _("Related Payments"),
            'context': {'create': False},
        }

    def _create_derived_flow(self, transmission_type):
        """Create correction (MO) or rectificative (RE) flow."""
        self.ensure_one()
        if self.state not in {'done', 'pending', 'error'}:
            raise UserError(_("Only sent flows can generate a derived flow."))
        reference = self if transmission_type == 'MO' else self._get_latest_period_flow()
        new_flow = self.copy({
            'name': self._default_name(),
            'state': 'draft',
            **self._payload_reset(),
            'acknowledgement_status': 'pending',
            'acknowledgement_details': False,
            'last_send_datetime': False,
            'send_datetime': False,
            'transmission_type': transmission_type,
            'transmission_reference': reference.transport_identifier or False,
            'transmission_reference_type': reference.transmission_type or 'IN',
            'is_correction': True,
            'tracking_id': False,
            'revision': 0,
            'move_ids': [Command.set(self.move_ids.ids)],
        })
        new_flow._ensure_tracking_id()
        _logger.info("%s flow %s created from %s", transmission_type, new_flow.id, self.id)
        new_link = f"<a href=#id={new_flow.id}&model=l10n.fr.pdp.flow&view_type=form>{new_flow.display_name}</a>"
        origin_link = f"<a href=#id={self.id}&model=l10n.fr.pdp.flow&view_type=form>{self.display_name}</a>"
        kind = _("Rectificative") if transmission_type == 'RE' else _("Corrective")
        self.message_post(body=_("%(kind)s flow created: %(link)s", kind=kind, link=new_link), subtype_xmlid="mail.mt_note")
        new_flow.message_post(body=_("Created from %(origin)s", origin=origin_link), subtype_xmlid="mail.mt_note")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n.fr.pdp.flow',
            'view_mode': 'form',
            'res_id': new_flow.id,
            'target': 'current',
        }

    def _get_latest_period_flow(self):
        """Get most recent sent flow for same period."""
        domain = [
            ('company_id', '=', self.company_id.id),
            ('report_kind', '=', self.report_kind),
            ('document_type', '=', self.document_type),
            ('currency_id', '=', self.currency_id.id),
            ('reporting_date', '=', self.reporting_date),
            ('state', 'in', ('done', 'pending')),
        ]
        period_flows = self.search(domain).sorted('create_date')
        return period_flows[-1] if period_flows else self

    def action_create_correction_flow(self):
        """Create corrective (MO) flow."""
        return self._create_derived_flow('MO')

    def action_create_rectificative_flow(self):
        """Create rectificative (RE) flow."""
        if self.state not in {'done', 'pending'}:
            raise UserError(_("Only flows already submitted can be replaced."))
        return self._create_derived_flow('RE')

    # -------------------------------------------------------------------------
    # Corrections from move changes
    # -------------------------------------------------------------------------

    @api.model
    def _create_corrections_for_moves(self, moves):
        """Create MO flows for posted invoices already sent."""
        flow_model = self.env['l10n.fr.pdp.flow']
        for move in moves:
            if move.state != 'posted' or not move.is_sale_document(include_receipts=True):
                continue
            sent_flows = move.l10n_fr_pdp_flow_ids.filtered(
                lambda f: f.state in {'pending', 'done'} and f.report_kind == 'transaction',
            )
            if not sent_flows:
                continue
            existing = flow_model.search(
                [
                    ('report_kind', '=', 'transaction'),
                    ('state', 'in', ('draft', 'building', 'ready', 'error')),
                    ('is_correction', '=', True),
                    ('move_ids', 'in', move.ids),
                ],
                limit=1,
            )
            if existing:
                continue
            reference_flow = sent_flows.sorted(lambda f: f.send_datetime or f.create_date)[-1]
            vals = {
                'name': flow_model._default_name(),
                'company_id': move.company_id.id,
                'reporting_date': reference_flow.reporting_date or (move.invoice_date or move.date),
                'currency_id': reference_flow.currency_id.id,
                'document_type': reference_flow.document_type,
                'flow_type': reference_flow.flow_type,
                'transaction_type': reference_flow.transaction_type,
                'report_kind': 'transaction',
                'state': 'draft',
                'is_correction': True,
                'transmission_type': 'MO',
                'transmission_reference': reference_flow.transport_identifier or False,
                'transmission_reference_type': reference_flow.transmission_type or 'IN',
                'period_start': reference_flow.period_start,
                'period_end': reference_flow.period_end,
                'periodicity_code': reference_flow.periodicity_code,
                'issue_datetime': fields.Datetime.now(),
                'move_ids': [Command.set(move.ids)],
                'payload': False,
                'payload_filename': False,
                'payload_sha256': False,
                'acknowledgement_status': 'pending',
                'acknowledgement_details': False,
                'last_send_datetime': False,
                'send_datetime': False,
                'attempt_count': 0,
                'transport_identifier': False,
                'transport_status': False,
                'transport_message': False,
                'error_move_ids': [Command.clear()],
                'error_move_message': False,
            }
            new_flow = flow_model.create(vals)
            new_flow._update_reference_name()
            new_flow._ensure_tracking_id()
