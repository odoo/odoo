import base64
import calendar
import json
import logging
import re
import uuid

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import Command, api, fields, models, tools, _
from odoo.exceptions import UserError

from ..utils.vat import is_valid_vat
from .pdp_payload import PdpPayloadBuilder

_logger = logging.getLogger(__name__)

# Blocking rejection codes from Flux 10 v1.2 specification (Tableau 14)
# REJ_UNI is handled separately as duplicate acknowledgement (G8.05).
REJECTION_CODES = {
    'REJ_PER',  # Contrôle du format/période
    'REJ_COH',  # Contrôle de cohérence
}
DUPLICATE_ACK_CODES = {
    'REJ_UNI',  # Contrôle d'unicité (treated as duplicate transmission)
}
PDP_INTERFACE_CODE = 'FFE1025A'
PDP_APP_CODE_QUAL = 'PPF262'  # ODOO raccordement EDI QUAL
PDP_APP_CODE_PROD = 'PDP257'  # ODOO raccordement EDI PROD
PDP_APP_CODE_FALLBACK_QUAL = 'PPF000'
PDP_APP_CODE_FALLBACK_PROD = 'PDP000'
PDP_FILENAME_ID_LENGTH = 19


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
            ('pending', "Pending"),
            ('building', "Building"),
            ('ready', "Ready"),
            ('error', "Error"),
            ('cancelled', "Cancelled"),
            ('sent', "Sent"),
            ('completed', "Completed"),
        ],
        string="Status",
        required=True,
        default='pending',
        index=True,
    )
    payload = fields.Binary(string="Payload", attachment=True, help="XML payload sent to the PDP API.")
    payload_filename = fields.Char(string="Payload Filename")
    transport_identifier = fields.Char(string="Transport Identifier", help="Identifier returned by the PDP transport API.")
    transport_status = fields.Char(string="Transport Status", help="Raw status returned by the PDP transport API.")
    transport_message = fields.Text(string="Transport Message", help="Additional message or error returned by the PDP transport API.")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
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
    operation_type = fields.Selection(
        selection=[('sale', "Sales"), ('purchase', "Acquisitions")],
        string="Operation Type",
        required=True,
        default='sale',
        index=True,
        help="Defines whether the flow reports sales or acquisition transactions.",
    )
    transaction_type = fields.Selection(
        selection=[('b2c', "B2C Domestic"), ('international', "International B2B"), ('mixed', "Mixed Scope")],
        string="Transaction Scope",
        default='b2c',
        required=True,
        index=True,
    )
    transmission_type = fields.Selection(
        selection=[('IN', "Initial"), ('RE', "Rectificative")],
        string="Transmission Type",
        required=True,
        default='IN',
        help="Type of transmission per Flux 10 v1.2: IN (Initial) or RE (Rectificative).",
    )
    issue_datetime = fields.Datetime(
        string="Issue Datetime",
        default=fields.Datetime.now,
        help="Timestamp at which the transmission is generated (TT-3).",
        copy=False,
    )
    tracking_id = fields.Char(string="Tracking Identifier", help="External tracking identifier sent to the Flow Service.", copy=False)
    has_payload = fields.Boolean(string="Has Payload", compute='_compute_has_payload', readonly=True)
    has_error_moves = fields.Boolean(string="Has Error Moves", compute='_compute_has_error_moves', readonly=True)
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
        comodel_name='res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    move_ids = fields.Many2many(
        comodel_name='account.move',
        relation='l10n_fr_pdp_flow_move_rel',
        column1='flow_id',
        column2='move_id',
        string="Source Moves",
        help="Invoices that produced this flow.",
    )
    payment_move_count = fields.Integer(string="Payments", compute='_compute_payment_move_count')
    error_move_ids = fields.Many2many(
        comodel_name='account.move',
        relation='l10n_fr_pdp_flow_error_move_rel',
        column1='flow_id',
        column2='move_id',
        string="Invalid Invoices",
        help="Invoices excluded from the payload because of validation errors.",
        copy=False,
    )
    error_move_message = fields.Text(string="Invalid Invoice Details", copy=False)
    company_periodicity = fields.Selection(
        related='company_id.l10n_fr_pdp_periodicity',
        string="Transaction Periodicity",
        readonly=True,
    )
    company_payment_periodicity = fields.Selection(
        related='company_id.l10n_fr_pdp_payment_periodicity',
        string="Payment Periodicity",
        readonly=True,
    )
    next_deadline_start = fields.Date(string="Next Send Window Start", compute='_compute_deadline_preview', store=True)
    next_deadline_end = fields.Date(string="Next Send Window End", compute='_compute_deadline_preview', store=True)
    period_status = fields.Selection(
        selection=[('open', "Open"), ('grace', "Grace"), ('closed', "Closed")],
        string="Period Status",
        compute='_compute_period_status',
        store=False,
        help="Current status of the reporting period: Open (before grace), Grace (can send), Closed (after deadline).",
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends('payload')
    def _compute_has_payload(self):
        for flow in self:
            flow.has_payload = bool(flow.payload)

    @api.depends('error_move_ids')
    def _compute_has_error_moves(self):
        for flow in self:
            flow.has_error_moves = bool(flow.error_move_ids)

    @api.depends('period_end', 'reporting_date', 'next_deadline_start', 'next_deadline_end')
    def _compute_period_status(self):
        """Compute the current status of the reporting period."""
        today = fields.Date.context_today(self)
        for flow in self:
            flow.period_status = flow._get_period_status(today)

    def _get_period_status(self, today=None):
        """Return period status (open/grace/closed) for a given date."""
        self.ensure_one()
        today = fields.Date.to_date(today or fields.Date.context_today(self))
        period_end = fields.Date.to_date(self.period_end or self.reporting_date)
        due_date = fields.Date.to_date(self.next_deadline_end) if self.next_deadline_end else False
        if not due_date:
            # `next_deadline_end` is a stored compute and may be unavailable on just-created flows.
            # Recompute from period data to avoid incorrectly freezing status to `open`.
            deadline_window = self._compute_deadline_window(today)
            due_date = deadline_window[1] if deadline_window else False

        # Period lifecycle definition:
        # - open: inside the reporting period (period_start..period_end inclusive)
        # - grace: after period_end and before the due date (exclusive)
        # - closed: due date day and after
        if not period_end or not due_date or today <= period_end:
            return 'open'
        if today < due_date:
            return 'grace'
        return 'closed'

    @api.depends(
        'period_start',
        'period_end',
        'report_kind',
        'company_id.l10n_fr_pdp_periodicity',
        'company_id.l10n_fr_pdp_payment_periodicity',
        'company_id.l10n_fr_pdp_deadline_override_start',
        'company_id.l10n_fr_pdp_deadline_override_end',
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
            if reporting_date := vals.get('reporting_date'):
                vals.setdefault('period_start', reporting_date)
                vals.setdefault('period_end', reporting_date)
        records = super().create(vals_list)
        records._update_reference_name()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'reporting_date' in vals and 'period_start' not in vals and 'period_end' not in vals:
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
        company_partner = move.company_id.partner_id.commercial_partner_id
        company_vat = company_partner.vat
        company_country = company_partner.country_id.code if company_partner.country_id else None
        if move.state == 'posted' and move.is_sale_document(include_receipts=True) and not move.is_move_sent:
            errors.append(_("Invoice/credit note has not been sent to the customer."))
        if move._get_l10n_fr_pdp_transaction_type() == 'international':
            partner = move.commercial_partner_id
            vat = partner.vat
            country_code = partner.country_id.code if partner.country_id else None
            if not vat:
                errors.append(_("Missing buyer VAT."))
            elif not is_valid_vat(vat, country_code):
                errors.append(_("Invalid buyer VAT (%(vat)s).", vat=vat))
            if not company_vat:
                requires_tt122 = self._requires_fiscal_representative_vat(move)
                representative_vat = (move.company_id.l10n_fr_pdp_fiscal_representative_vat or '').strip()
                if requires_tt122:
                    if not representative_vat:
                        errors.append(_("Missing seller fiscal representative VAT (TT-122)."))
                    elif not is_valid_vat(representative_vat, company_country):
                        errors.append(_("Invalid seller fiscal representative VAT (%(vat)s).", vat=representative_vat))
                else:
                    errors.append(_("Missing seller VAT."))
            elif not is_valid_vat(company_vat, company_country):
                errors.append(_("Invalid seller VAT (%(vat)s).", vat=company_vat))
        if move.is_purchase_document(include_receipts=False) and self._is_international_partner_for_purchase(move):
            supplier = move.commercial_partner_id
            supplier_vat = supplier.vat
            supplier_country = supplier.country_id.code if supplier.country_id else None
            if not supplier_vat:
                errors.append(_("Missing supplier VAT."))
            elif not is_valid_vat(supplier_vat, supplier_country):
                errors.append(_("Invalid supplier VAT (%(vat)s).", vat=supplier_vat))
            if not company_vat:
                errors.append(_("Missing buyer VAT."))
            elif not is_valid_vat(company_vat, company_country):
                errors.append(_("Invalid buyer VAT (%(vat)s).", vat=company_vat))
        return errors

    def _requires_fiscal_representative_vat(self, move):
        """Return True when TT-122 fallback can apply for the seller on this move."""
        self.ensure_one()
        if move._get_l10n_fr_pdp_transaction_type() != 'international':
            return False
        taxes = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product').mapped('tax_ids')
        return any((tax.l10n_fr_pdp_vatex_code or '').strip() for tax in taxes)

    def _is_international_partner_for_purchase(self, move):
        """Return True when a vendor bill partner is treated as international."""
        return move._is_international_partner_for_purchase()

    def _update_error_moves(self, invalid_moves, log_event=False):
        self.ensure_one()
        invalid_ids = list(invalid_moves)
        invalid_move_records = self.env['account.move'].browse(invalid_ids)
        # Avoid spamming chatter if the same invalid set was already recorded.
        if invalid_move_records.sorted('id') == self.error_move_ids.sorted('id') and self.error_move_message:
            return
        self.error_move_ids = [Command.set(invalid_ids)]
        details = []
        for move_id, reasons in invalid_moves.items():
            move = self.env['account.move'].browse(move_id)
            details.append('%s: %s' % (move.display_name, '; '.join(reasons)))
            # Only post on the move if the content differs to limit spam.
            errors_html = '<br/>'.join(tools.html_escape(reason) for reason in reasons)
            body = tools.html_escape(
                _("Excluded from PDP flow %(flow)s due to validation errors:", flow=self.display_name)
            )
            if errors_html:
                body = '%s<br/>%s' % (body, errors_html)
            last_body = move.message_ids[:1].body if move.message_ids else None
            if last_body != body:
                move.message_post(body=body, subtype_xmlid='mail.mt_note')
        self.error_move_message = '\n'.join(details)
        if log_event:
            self._log_cron_event(
                _("Flow contains %(count)s invalid invoice(s) that were excluded.", count=len(invalid_move_records)),
            )

    def _clear_error_moves(self):
        self.error_move_ids = [Command.clear()]
        self.error_move_message = False

    # -------------------------------------------------------------------------
    # Business Methods - Payload Building
    # -------------------------------------------------------------------------

    def _build_payload(self):
        """Build single XML payload for the entire flow period."""
        open_states = {'pending', 'building', 'ready', 'error'}
        for flow in self:
            if flow.state not in open_states:
                raise UserError(_("Flow %(name)s has already been sent.", name=flow.name))
            flow._ensure_tracking_id()
            flow.state = 'building'

            # Validate all moves in the flow
            invalid_acc = {}
            valid_moves, _invalids = flow._filter_valid_moves(
                flow.move_ids, invalid_collector=invalid_acc, log_event=True,
            )

            # Update error moves tracking
            if invalid_acc:
                flow._update_error_moves(invalid_acc)
            else:
                flow._clear_error_moves()

            # Determine state based on period status and validation errors
            has_errors = bool(invalid_acc)
            period_status = flow._get_period_status()
            if period_status == 'open':
                # During open period, always stay in pending state
                new_state = 'pending'
            elif has_errors:
                # During grace/closed period with errors
                new_state = 'error'
            else:
                # During grace/closed period without errors
                new_state = 'ready'

            # If no valid moves, keep flow in computed functional state and DON'T set transport status.
            # Note: we intentionally keep "error" in closed periods so users can still fix and rebuild.
            if not valid_moves:
                flow.write({
                    **flow._payload_reset(),
                    'state': new_state,
                })
                flow._message_post_once(_("Payload build failed: no valid invoices."))
                continue

            # Build single XML payload for ALL moves (entire period)
            builder = PdpPayloadBuilder(flow)
            new_revision = (flow.revision or 0) + 1
            build_result = builder.build(valid_moves, slice_date=None, invalid_collector=invalid_acc)

            # Store payload on flow
            flow.write({
                'payload': build_result['payload'],
                'payload_filename': build_result['filename'],
                'state': new_state,
                'revision': new_revision,
                'acknowledgement_status': 'pending',
                'acknowledgement_details': False,
                'issue_datetime': fields.Datetime.now(),
            })

            # Keep a single visible payload attachment per flow and replace it on rebuild.
            flow._upsert_payload_attachment(build_result['filename'], build_result['payload'])

            # Log build completion
            if invalid_acc:
                flow._message_post_once(_(
                    "Payload built with %(valid)s valid invoice(s) and %(invalid)s error(s).",
                    valid=len(valid_moves),
                    invalid=len(invalid_acc),
                ))
            else:
                flow._message_post_once(_(
                    "Payload built successfully with %(count)s invoice(s).",
                    count=len(valid_moves),
                ))

    def _payload_reset(self):
        """Return dict to clear payload-related fields."""
        return {'payload': False, 'payload_filename': False}

    # -------------------------------------------------------------------------
    # Business Methods - Sending
    # -------------------------------------------------------------------------

    def action_send(self):
        """Send flow payload to transport gateway."""
        for flow in self:
            flow._ensure_tracking_id()
            ignore_errors = self.env.context.get('ignore_error_invoices')
            if ignore_errors and flow.transmission_type == 'RE':
                raise UserError(_("Rectificative flows must include all invoices; you cannot exclude invalid invoices."))

            # Build payload if not ready
            if flow.state not in {'ready', 'error'} and not flow.payload:
                flow._build_payload()

            # Check if we can send
            has_valid_moves = bool(flow.move_ids - flow.error_move_ids)
            can_send = flow.state == 'ready' or (flow.state == 'error' and ignore_errors and has_valid_moves)

            if not can_send:
                continue

            # If in error state but ignoring errors, rebuild with only valid moves
            if flow.state == 'error' and ignore_errors:
                # Temporarily clear error moves for rebuild
                valid_moves = flow.move_ids - flow.error_move_ids
                if not valid_moves:
                    flow.write({
                        'transport_status': 'ERROR',
                        'transport_message': _("No valid invoices in this flow."),
                    })
                    continue

                # Rebuild payload with only valid moves
                builder = PdpPayloadBuilder(flow)
                build_result = builder.build(valid_moves, slice_date=None, invalid_collector={})
                flow.write({
                    'payload': build_result['payload'],
                    'payload_filename': build_result['filename'],
                    'state': 'ready',
                })

                # Keep a single visible payload attachment per flow and replace it on rebuild.
                flow._upsert_payload_attachment(build_result['filename'], build_result['payload'])

            # Send single payload to proxy.
            response = flow._send_to_proxy()
            transport_state = flow._map_transport_status(response)
            ack_status, status, ack_details, transport_status, rejected_move_ids = flow._process_acknowledgement(response, transport_state)
            send_datetime = fields.Datetime.now()
            rejected_moves = self.env['account.move'].browse(rejected_move_ids)
            write_vals = {
                'transport_identifier': response.get('id'),
                'transport_status': transport_status or response.get('status'),
                'transport_message': response.get('message'),
                'state': status,
                'last_send_datetime': send_datetime,
                'send_datetime': send_datetime if status in {'sent', 'completed'} else flow.send_datetime,
                'issue_datetime': send_datetime if status in {'sent', 'completed'} else flow.issue_datetime,
                'acknowledgement_status': ack_status,
                'acknowledgement_details': ack_details,
            }
            if rejected_moves:
                merged_error_moves = (flow.error_move_ids | rejected_moves).ids
                write_vals.update({
                    'error_move_ids': [Command.set(merged_error_moves)],
                    'error_move_message': flow._get_partial_rejection_error_message(rejected_moves),
                })

            # Update flow with transport response
            flow.write(write_vals)
            if rejected_moves:
                flow._post_partial_rejection_messages(rejected_moves)
            flow._upsert_transport_response_attachment({
                'transport': response,
                'acknowledgement_status': ack_status,
                'acknowledgement_details': ack_details or [],
                'flow_state': status,
                'sent_at': fields.Datetime.to_string(send_datetime),
            })

            # Handle correction flow for error invoices if requested
            if flow.transmission_type == 'IN' and flow.error_move_ids and ignore_errors and status in {'sent', 'completed'}:
                flow._schedule_correction_for_error_moves()

            # Post audit messages on sent moves
            if status in {'sent', 'completed'}:
                flow._post_sent_message_on_moves()
                flow._mark_payment_events_as_reported()

            # Log send result
            flow._message_post_once(_(
                "Flow sent: status %(status)s, transport %(transport)s. %(details)s",
                status=status,
                transport=response.get('id') or _("n/a"),
                details=response.get('message') or '',
            ))
        return True

    def _post_sent_message_on_moves(self):
        """Post audit message on successfully sent moves."""
        self.ensure_one()
        sent_moves = self.move_ids - self.error_move_ids
        if not sent_moves:
            return
        flow_link = Markup('<a href="/web#id=%s&amp;model=l10n.fr.pdp.flow&amp;view_type=form">%s</a>') % (self.id, self.name)
        body = _("E-reports %s sent", flow_link)
        for move in sent_moves:
            move.message_post(body=body, subtype_xmlid='mail.mt_note')

    def _post_partial_rejection_messages(self, rejected_moves):
        """Post an audit note on each move rejected by the proxy acknowledgement."""
        self.ensure_one()
        for move in rejected_moves:
            move.message_post(
                body=_("Rejected by PDP acknowledgement for flow %s.", self.display_name),
                subtype_xmlid='mail.mt_note',
            )

    def _get_partial_rejection_error_message(self, rejected_moves):
        """Merge existing validation errors with partial transport rejections."""
        self.ensure_one()
        rejection_lines = [
            _("%(move)s: rejected by PDP acknowledgement after transport send.", move=move.display_name)
            for move in rejected_moves
        ]
        existing_lines = [line for line in (self.error_move_message or '').splitlines() if line]
        return '\n'.join(existing_lines + rejection_lines)

    def _mark_payment_events_as_reported(self):
        """Mark pending unreconcile payment events as reported after successful send."""
        self.ensure_one()
        if self.report_kind != 'payment' or not self.move_ids:
            return
        domain = [
            ('state', '=', 'pending'),
            ('move_id', 'in', self.move_ids.ids),
        ]
        # Keep date upper-bound to avoid marking future events that were not part
        # of the sent flow, but do not enforce period_start: late regularizations
        # can be sent in corrective windows.
        if self.period_end:
            domain.append(('event_date', '<=', self.period_end))
        events = self.env['l10n.fr.pdp.payment.event'].sudo().search(domain)
        if events:
            events.write({
                'state': 'reported',
                'reported_flow_id': self.id,
            })

    def _get_pdp_proxy_user(self):
        self.ensure_one()
        proxy_user = self.company_id.account_edi_proxy_client_ids.filtered(
            lambda user: user.proxy_type == 'pdp'
        )[:1]
        if proxy_user:
            return proxy_user
        if tools.config['test_enable']:
            return False
        raise UserError(_("No active PDP proxy user is configured for company %(company)s.", company=self.company_id.display_name))

    def _send_to_proxy(self):
        self.ensure_one()
        if not self.payload or not self.payload_filename:
            raise UserError(_("The flow payload is missing. Build the payload before sending."))
        proxy_user = self._get_pdp_proxy_user()
        payload_value = self.payload.decode() if isinstance(self.payload, bytes) else self.payload
        payload_doc = {
            'flow_number': 10,
            'filename': self.payload_filename,
            'ubl': payload_value,
            'external_ref': self.tracking_id,
        }
        if not proxy_user:
            # Keep local test runs deterministic without requiring a remote proxy setup.
            return {
                'id': str(uuid.uuid4()),
                'flow_id': self.tracking_id,
                'status': 'DRAFT',
                'message': _("PDP proxy mocked in test mode."),
                'acknowledgement': [],
            }
        result = proxy_user._l10n_fr_pdp_call_proxy('/api/pdp/1/send_document', {
            'documents': [payload_doc],
        })
        ppf_messages = result.get('ppf_messages') or []
        if not ppf_messages:
            raise UserError(_("The PDP proxy did not return a flow tracking identifier."))
        proxy_message = ppf_messages[0]
        return {
            'id': proxy_message.get('uuid') or proxy_message.get('flow_id'),
            'flow_id': proxy_message.get('flow_id'),
            'status': (proxy_message.get('state') or '').upper() or 'DRAFT',
            'message': result.get('message') or '',
            'acknowledgement': proxy_message.get('acknowledgement') or [],
        }

    def _map_transport_status(self, response):
        """Map API status to internal state."""
        raw_status = (response or {}).get('status', '').upper()
        mapping = {
            'ACCEPTED': 'completed',
            'DELIVERED': 'completed',
            'DONE': 'completed',
            'ERROR': 'error',
            'REFUSED': 'error',
            'DRAFT': 'sent',
            'PROCESSING': 'sent',
        }
        return mapping.get(raw_status, 'sent')

    def _normalize_invoice_reference(self, value):
        """Normalize references for resilient matching against acknowledgement payloads."""
        return re.sub(r'\s+', '', (value or '').strip().upper())

    def _extract_ack_invoice_reference(self, ack):
        """Extract one invoice reference from an acknowledgement entry when available."""
        keys = (
            'invoice_id',
            'invoice_reference',
            'invoice_number',
            'document_id',
            'document_reference',
            'reference',
            'id',
            'tt19',
        )
        for key in keys:
            value = ack.get(key)
            if isinstance(value, str) and value.strip():
                return value
        invoice_block = ack.get('invoice')
        if isinstance(invoice_block, dict):
            for key in keys:
                value = invoice_block.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return False

    def _extract_rejected_invoice_refs(self, acknowledgement_entries):
        """Return normalized invoice references explicitly rejected by acknowledgement entries."""
        rejected_refs = set()
        for ack in acknowledgement_entries:
            ref = self._extract_ack_invoice_reference(ack)
            if ref:
                rejected_refs.add(self._normalize_invoice_reference(ref))
        return rejected_refs

    def _match_moves_by_invoice_refs(self, moves, rejected_refs):
        """Match rejected references to move identifiers used in Flux 10 payloads."""
        if not moves or not rejected_refs:
            return self.env['account.move']
        matched_moves = self.env['account.move']
        for move in moves:
            candidates = {
                self._normalize_invoice_reference(move.l10n_fr_pdp_invoice_reference or ''),
                self._normalize_invoice_reference(move.name or ''),
                self._normalize_invoice_reference(move.ref or ''),
            }
            if candidates.intersection(rejected_refs):
                matched_moves |= move
        return matched_moves

    def _process_acknowledgement(self, response, transport_state):
        """Derive acknowledgement status/state from gateway response."""
        ack_list = (response or {}).get('acknowledgement') or []
        # Default: stick to transport state and pending ack.
        ack_status = 'pending'
        flow_state = transport_state
        transport_status = False
        rejected_move_ids = []
        if not ack_list:
            return ack_status, flow_state, False, transport_status, rejected_move_ids

        # Detect rejection/duplicate acknowledgement codes per spec (Tableau 14)
        rejection_entries = []
        has_duplicate = False
        for ack in ack_list:
            code = (ack.get('code') or ack.get('reason_code') or '').upper()
            if code in REJECTION_CODES:
                rejection_entries.append(ack)
            if code in DUPLICATE_ACK_CODES:
                has_duplicate = True

        if rejection_entries:
            rejected_refs = self._extract_rejected_invoice_refs(rejection_entries)
            sent_moves = self.move_ids - self.error_move_ids
            rejected_moves = self._match_moves_by_invoice_refs(sent_moves, rejected_refs)
            if rejected_moves and len(rejected_moves) < len(sent_moves):
                # Rejet partiel: only impacted documents are marked as errors.
                ack_status = 'error'
                flow_state = 'completed'
                transport_status = 'PARTIAL_REJECTED'
                rejected_move_ids = rejected_moves.ids
            else:
                # Rejet global (or unknown granularity): keep strict global error behavior.
                ack_status = 'error'
                flow_state = 'error'
        elif has_duplicate:
            # Duplicate transmission (G8.05): no business error, keep flow as completed.
            ack_status = 'ok'
            flow_state = 'completed'
            transport_status = 'DUPLICATE'
        else:
            ack_status = 'ok'
            # If transport returned only 'sent', upgrade to completed on positive ack.
            if flow_state == 'sent':
                flow_state = 'completed'

        return ack_status, flow_state, ack_list, transport_status, rejected_move_ids

    def _extract_proxy_poll_error_message(self, payload):
        """Extract a readable error message from proxy polling payload."""
        if not payload:
            return False
        if isinstance(payload, dict):
            return payload.get('message') or json.dumps(payload)
        if isinstance(payload, str):
            try:
                decoded = json.loads(payload)
            except ValueError:
                return payload
            if isinstance(decoded, dict):
                return decoded.get('message') or payload
            return payload
        return str(payload)

    def _map_proxy_polled_message(self, message):
        """Map generic proxy message polling payload to flow updates."""
        raw_state = (message.get('state') or '').strip().lower()
        transport_status = raw_state.upper() if raw_state else False
        if raw_state == 'done':
            return {
                'state': 'completed',
                'acknowledgement_status': 'ok',
                'transport_status': transport_status,
                'transport_message': False,
            }
        if raw_state == 'error':
            return {
                'state': 'error',
                'acknowledgement_status': 'error',
                'transport_status': transport_status,
                'transport_message': self._extract_proxy_poll_error_message(message.get('error')),
            }
        if raw_state in {'processing', 'draft'}:
            return {
                'state': 'sent',
                'acknowledgement_status': 'pending',
                'transport_status': transport_status,
            }
        return {
            'state': False,
            'acknowledgement_status': False,
            'transport_status': transport_status,
        }

    @api.model
    def _cron_sync_transport_statuses(self):
        """Poll proxy message states and synchronize flow transport statuses."""
        companies = self.env['res.company'].search([('l10n_fr_pdp_enabled', '=', True)])
        if not companies:
            return True

        for company in companies:
            flows = self.search([
                ('company_id', '=', company.id),
                ('transport_identifier', '!=', False),
                ('state', 'in', ('sent', 'completed', 'error')),
                '|',
                ('acknowledgement_status', '=', 'pending'),
                ('transport_status', 'in', ('DRAFT', 'PROCESSING', 'PARTIAL_REJECTED')),
            ])
            if not flows:
                continue
            try:
                proxy_user = flows[:1]._get_pdp_proxy_user()
                if not proxy_user:
                    continue
                response = proxy_user._l10n_fr_pdp_call_proxy('/api/pdp/1/get_all_documents', {
                    'domain': {'direction': 'outgoing'},
                })
                messages = response.get('messages') or []
                messages_by_uuid = {msg.get('uuid'): msg for msg in messages if msg.get('uuid')}
                ack_uuids = []

                for flow in flows:
                    message = messages_by_uuid.get(flow.transport_identifier)
                    if not message:
                        continue
                    mapped = flow._map_proxy_polled_message(message)
                    write_vals = {}
                    if mapped.get('transport_status'):
                        write_vals['transport_status'] = mapped['transport_status']
                    if mapped.get('transport_message') is not None:
                        write_vals['transport_message'] = mapped.get('transport_message')
                    target_state = mapped.get('state')
                    if target_state and not (flow.state in {'completed', 'error'} and target_state == 'sent'):
                        write_vals['state'] = target_state
                    ack_status = mapped.get('acknowledgement_status')
                    if ack_status and not (flow.acknowledgement_status in {'ok', 'error'} and ack_status == 'pending'):
                        write_vals['acknowledgement_status'] = ack_status

                    if not write_vals:
                        continue
                    flow.write(write_vals)
                    flow._log_cron_event(
                        _("Proxy status synchronized by cron (status: %(status)s).",
                          status=flow.transport_status or flow.state)
                    )
                    ack_uuids.append(flow.transport_identifier)

                if ack_uuids:
                    proxy_user._l10n_fr_pdp_call_proxy('/api/pdp/1/ack', {
                        'message_uuids': sorted(set(ack_uuids)),
                    })
            except Exception:
                _logger.exception('Failed to synchronize PDP transport statuses for company %s', company.id)
        return True

    # -------------------------------------------------------------------------
    # Business Methods - Cron
    # -------------------------------------------------------------------------

    @api.model
    def _cron_send_ready_flows(self):
        """Cron job to send ready flows within their send window."""
        today = fields.Date.context_today(self)
        companies = self.env['res.company'].search([
            ('l10n_fr_pdp_enabled', '=', True),
            ('l10n_fr_pdp_send_mode', '=', 'auto'),
        ])
        if not companies:
            return True
        flows = self.search([('state', 'in', ('ready', 'error')), ('company_id', 'in', companies.ids)])
        for flow in flows:
            try:
                # IN sends within its window:
                # - no errors: send as soon as the window opens
                # - errors: send only on the last day (excluding invalid invoices)
                # RE sends immediately when ready.
                if flow.transmission_type == 'IN':
                    window = flow._compute_deadline_window(today)
                    if not window:
                        continue
                    window_start, window_end = window
                    if today < window_start:
                        continue
                    if today > window_end:
                        continue
                    if flow.error_move_ids:
                        if today != window_end:
                            continue
                        if not (flow.move_ids - flow.error_move_ids):
                            flow.write({
                                'state': 'cancelled',
                                'transport_status': 'CANCELLED',
                                'transport_message': _("Flow cancelled: all invoices are invalid at send deadline."),
                            })
                            flow._log_cron_event(_("Flow cancelled at deadline: all invoices are invalid."))
                            continue
                        ctx = {'ignore_error_invoices': True}
                    else:
                        ctx = {}
                else:
                    # RE flows: send immediately when ready (no deadline constraint)
                    if flow.state != 'ready' or flow.error_move_ids:
                        continue
                    ctx = {}
                flow.with_context(**ctx).with_company(flow.company_id).sudo().action_send()
                flow._log_cron_event(
                    _("Flow automatically sent by cron (status: %(status)s). %(extra)s",
                      status=flow.transport_status or flow.state,
                      extra=_("Invalid invoices were excluded.") if flow.error_move_ids else ""),
                )
            except Exception:
                _logger.exception('Failed to send PDP flow %s during cron', flow.id)
        return True

    def _schedule_correction_for_error_moves(self):
        """Create or update a rectificative (RE) flow after a partial IN send.

        Corrections use a RE transmission referencing the previous flow via TG-2/TT-5.
        RE is always a full replacement payload for the whole period (never a delta).
        """
        self.ensure_one()
        if not self.error_move_ids:
            return
        open_states = {'pending', 'building', 'ready', 'error'}
        re_flow = self.env['l10n.fr.pdp.flow'].search([
            ('company_id', '=', self.company_id.id),
            ('currency_id', '=', self.currency_id.id),
            ('flow_type', '=', self.flow_type),
            ('report_kind', '=', self.report_kind),
            ('period_start', '=', self.period_start),
            ('period_end', '=', self.period_end),
            ('periodicity_code', '=', self.periodicity_code),
            ('transmission_type', '=', 'RE'),
            ('is_correction', '=', True),
            ('state', 'in', tuple(open_states)),
        ], limit=1, order='create_date desc')

        if re_flow:
            re_flow._synchronize_moves(self.move_ids)
            # Keep the current invalid set visible on the rectificative flow.
            re_flow.error_move_ids = [Command.set(self.error_move_ids.ids)]
            re_flow.error_move_message = self.error_move_message
            re_flow._update_reference_name()
            re_flow._ensure_tracking_id()
            return

        new_flow = self.copy({
            'name': self._default_name(),
            'state': 'pending',
            **self._payload_reset(),
            'acknowledgement_status': 'pending',
            'acknowledgement_details': False,
            'last_send_datetime': False,
            'send_datetime': False,
            'transmission_type': 'RE',
            'is_correction': True,
            'transport_identifier': False,
            'transport_status': False,
            'transport_message': False,
            'attempt_count': 0,
            # Copy period information from parent
            'period_start': self.period_start,
            'period_end': self.period_end,
            'periodicity_code': self.periodicity_code,
            'reporting_date': self.reporting_date,
            # Full replacement payload for the period (never delta)
            'move_ids': [Command.set(self.move_ids.ids)],
            # Show what was excluded from the IN payload.
            'error_move_ids': [Command.set(self.error_move_ids.ids)],
            'error_move_message': self.error_move_message,
        })
        new_flow._update_reference_name()
        flow_link = Markup('<a href="/web#id=%s&amp;model=l10n.fr.pdp.flow&amp;view_type=form">%s</a>') % (new_flow.id, new_flow.display_name)
        self._log_cron_event(
            _("Rectificative flow %(flow)s created for %(count)s invalid invoice(s).",
              flow=flow_link,
              count=len(self.error_move_ids)),
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

        if periodicity == 'quarterly':
            # Quarterly: due on the 24th of the month following the quarter end
            anchor = period_end + relativedelta(months=1)
            last_day = calendar.monthrange(anchor.year, anchor.month)[1]
            send_day = min(24, last_day)
            return _one_day(anchor.replace(day=send_day))

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

    def _synchronize_moves(self, moves):
        """Update flow's moves, resetting payload if changed."""
        self.ensure_one()
        if self.move_ids == moves:
            return False
        values = {
            'move_ids': [Command.set(moves.ids)],
            **self._payload_reset(),
        }
        if self.state in {'pending', 'error'}:
            values['state'] = 'pending'
        self.write(values)
        return True

    # -------------------------------------------------------------------------
    # Business Methods - Tracking & Naming
    # -------------------------------------------------------------------------

    def _ensure_tracking_id(self):
        """Generate or normalize tracking ID."""
        reserved_ids = set()
        for flow in self.sorted('id'):
            candidate = flow.tracking_id or flow._generate_tracking_id()
            unique_tracking_id = flow._generate_unique_tracking_id(candidate, reserved_ids)
            if flow.tracking_id != unique_tracking_id:
                flow.tracking_id = unique_tracking_id

    def _generate_unique_tracking_id(self, candidate, reserved_ids=None):
        """Return a unique TT-1 identifier per company."""
        self.ensure_one()
        reserved_ids = reserved_ids if reserved_ids is not None else set()
        max_length = 50
        base = self._sanitize_token(candidate, default='TRACKING').upper()[:max_length]
        current = base
        suffix_idx = 1

        def _is_taken(token):
            return bool(self.search_count([
                ('company_id', '=', self.company_id.id),
                ('tracking_id', '=', token),
                ('id', '!=', self.id),
            ]))

        while current in reserved_ids or _is_taken(current):
            suffix = f'_{suffix_idx}'
            current = f"{base[:max_length - len(suffix)]}{suffix}"
            suffix_idx += 1

        reserved_ids.add(current)
        return current

    def _generate_tracking_id(self):
        """Generate unique tracking ID from company and flow attributes."""
        self.ensure_one()
        company = self.company_id
        siren = (company.siret or '')[:9]
        reporting_token = self._format_date(self.period_end or self.reporting_date) if (self.period_end or self.reporting_date) else fields.Date.context_today(self)
        currency = self.currency_id or company.currency_id
        parts = [
            siren or str(company.id),
            (self.report_kind or '')[:3],
            (self.operation_type or '')[:1],
            (self.transaction_type or '')[:3],
            (currency.name if currency else '')[:3],
            (self.transmission_type or '')[:2],
            str(reporting_token),
        ]
        return self._sanitize_token('_'.join(p for p in parts if p), default='TRACKING').upper()

    def _is_pdp_test_env(self):
        """Return True when PDP_TEST_ENV is set for QUAL environment."""
        param = self.env['ir.config_parameter'].sudo().get_param('PDP_TEST_ENV', '')
        return str(param).strip().lower() in {'1', 'true', 'yes', 'y', 't'}

    def _get_application_code(self):
        """Return PDP application code for EDI naming rules."""
        is_qual = self._is_pdp_test_env()
        code = PDP_APP_CODE_QUAL if is_qual else PDP_APP_CODE_PROD
        if not code:
            code = PDP_APP_CODE_FALLBACK_QUAL if is_qual else PDP_APP_CODE_FALLBACK_PROD
        return self._sanitize_token(code, default='APP').upper()

    def _build_filename_identifier(self):
        """Build 19-character alphanumeric identifier for EDI filenames."""
        self.ensure_one()
        self._ensure_tracking_id()
        base = self.tracking_id or uuid.uuid4().hex
        token = re.sub(r'[^A-Za-z0-9]+', '', base).upper()
        if len(token) < PDP_FILENAME_ID_LENGTH:
            # Generate additional alphanumeric characters from UUID to reach required length
            additional = uuid.uuid4().hex.upper()
            token = (token + additional)[:PDP_FILENAME_ID_LENGTH]
        return token[:PDP_FILENAME_ID_LENGTH]

    def _sanitize_token(self, value, default='FLOW'):
        """Clean token for use in filenames and identifiers."""
        value = (value or '').strip()
        if not value:
            return default
        # remove non-alphanumeric characters
        return re.sub(r'[^A-Za-z0-9_]+', '_', value)[:50] or default

    def _update_reference_name(self):
        """Set human-readable flow name based on period."""
        for flow in self:
            date_ref = flow.period_start or flow.reporting_date
            if not date_ref:
                continue
            date_ref = fields.Date.to_date(date_ref)

            # Type (Transaction/Acquisition/Payment)
            if flow.report_kind == 'payment':
                flow_type = _("Payment")
            elif flow.operation_type == 'purchase':
                flow_type = _("Acquisition")
            else:
                flow_type = _("Transaction")

            # Date format: MM/YYYY with optional Decade
            date_str = f"{date_ref.strftime('%m')}/{date_ref.strftime('%Y')}"
            if flow.periodicity_code == 'D':
                day = date_ref.day
                decade = 1 if day <= 10 else (2 if day <= 20 else 3)
                date_str = f"{date_str} Décade {decade}"

            # Transmission type (v1.2: IN or RE only)
            trans_type = _("Rectificative") if flow.transmission_type == 'RE' else _("Initial")

            # Format: Type - Date - Transmission Type
            flow.name = f"{flow_type} - {date_str} - {trans_type}"

    def _build_filename(self, extension='xml'):
        """Generate EDI-compliant filename for payload."""
        self.ensure_one()
        self._ensure_tracking_id()
        app_code = self._get_application_code()
        flow_id = self._build_filename_identifier()
        return f'{PDP_INTERFACE_CODE}_{app_code}_{app_code}{flow_id}.{extension}'

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

    def _message_post_once(self, body, subtype='mail.mt_note'):
        """Post message if it differs from the last one to avoid chatter spam."""
        self.ensure_one()
        last_body = self.message_ids[:1].body if self.message_ids else None
        if last_body == body:
            return
        self.message_post(body=body, subtype_xmlid=subtype)

    def _upsert_payload_attachment(self, filename, payload_b64):
        """Create or replace the visible XML attachment for this flow."""
        self.ensure_one()
        Attachment = self.env['ir.attachment']
        existing_xml = Attachment.search([
            ('res_model', '=', 'l10n.fr.pdp.flow'),
            ('res_id', '=', self.id),
            ('mimetype', '=', 'application/xml'),
        ], order='id desc')
        existing = existing_xml[:1]
        vals = {
            'name': filename,
            'datas': payload_b64,
            'res_model': 'l10n.fr.pdp.flow',
            'res_id': self.id,
            'type': 'binary',
            'mimetype': 'application/xml',
        }
        if existing:
            existing.write(vals)
            # Avoid accumulating stale XML payloads on repeated builds.
            (existing_xml - existing).unlink()
        else:
            Attachment.create(vals)

    def _upsert_transport_response_attachment(self, response_payload):
        """Create or replace the JSON attachment containing latest transport response."""
        self.ensure_one()
        Attachment = self.env['ir.attachment']
        base_name = self.payload_filename or self.name or f"flow_{self.id}.xml"
        filename = (
            f"{base_name[:-4]}_transport_response.json"
            if base_name.lower().endswith('.xml')
            else f"{base_name}_transport_response.json"
        )
        datas = base64.b64encode(
            json.dumps(response_payload or {}, ensure_ascii=False, indent=2).encode('utf-8')
        )
        existing = Attachment.search([
            ('res_model', '=', 'l10n.fr.pdp.flow'),
            ('res_id', '=', self.id),
            ('name', '=', filename),
            ('mimetype', '=', 'application/json'),
        ], limit=1, order='id desc')
        vals = {
            'name': filename,
            'datas': datas,
            'res_model': 'l10n.fr.pdp.flow',
            'res_id': self.id,
            'type': 'binary',
            'mimetype': 'application/json',
        }
        if existing:
            existing.write(vals)
        else:
            Attachment.create(vals)

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
                'state': 'pending',
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
        _logger.info('Manual payload build triggered for flows: %s', self.ids)
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
        _logger.info('Manual transport submission triggered for flows: %s', self.ids)
        return self.with_context(ctx).action_send()

    def action_send_ignore_errors(self):
        """Send flow ignoring error invoices."""
        return self.with_context(ignore_error_invoices=True).action_send_from_ui()

    def action_download_payload(self):
        """Download flow payload as XML file."""
        self.ensure_one()
        if not self.payload:
            raise UserError(_("This flow has no payload yet. Build it before downloading."))
        filename = self.payload_filename or self._build_filename()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/payload?download=true&filename={filename}',
            'target': 'self',
        }

    def _action_open_moves(self, moves, name, context=None):
        """Helper to open list view of account moves.

        Args:
            moves: Recordset of account.move to display
            name: Window title
            context: Optional context dict

        Returns:
            dict: Action to open moves list view
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
            'name': name,
            'context': context or {},
        }

    def action_view_error_moves(self):
        """Open list view of invalid invoices."""
        return self._action_open_moves(
            self.error_move_ids,
            _("Invalid Invoices"),
        )

    def action_open_send_wizard(self):
        """Open send wizard if errors exist, otherwise send directly."""
        self.ensure_one()
        if not self.error_move_ids:
            return self.action_send_from_ui()
        view = self.env.ref('l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_send_wizard_form', raise_if_not_found=False)
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
        return self._action_open_moves(
            self.move_ids,
            _("Related Invoices"),
            {'create': False, 'group_by': ['move_type']},
        )

    def _get_payment_entries(self):
        """Return payment/bank moves linked to this flow's invoices."""
        payments = self.env['account.move'].browse()
        for move in self.move_ids:
            if move.move_type == 'out_receipt':
                payments |= move
            for partial in move._get_all_reconciled_invoice_partials():
                aml = partial.get('aml')
                if aml:
                    payments |= aml.move_id
        return payments

    def action_view_payments(self):
        """Open list view of related payment entries."""
        self.ensure_one()
        payments = self._get_payment_entries()
        return self._action_open_moves(
            payments,
            _("Related Payments"),
            {'create': False},
        )

    def action_create_rectificative_flow(self):
        """Create rectificative (RE) flow (TG-2 removed from specs — no references block)."""
        self.ensure_one()
        if self.state not in {'completed', 'sent'}:
            raise UserError(_("Only flows already submitted can be rectified."))

        new_flow = self.copy({
            'name': self._default_name(),
            'state': 'pending',
            **self._payload_reset(),
            'acknowledgement_status': 'pending',
            'acknowledgement_details': False,
            'last_send_datetime': False,
            'send_datetime': False,
            'transmission_type': 'RE',
            'is_correction': True,
            'tracking_id': False,
            'revision': 0,
            'move_ids': [Command.set(self.move_ids.ids)],
        })
        new_flow._ensure_tracking_id()
        _logger.info('RE flow %s created from %s', new_flow.id, self.id)

        # Chatter messages
        new_link = Markup('<a href="/web#id=%s&amp;model=l10n.fr.pdp.flow&amp;view_type=form">%s</a>') % (new_flow.id, new_flow.display_name)
        origin_link = Markup('<a href="/web#id=%s&amp;model=l10n.fr.pdp.flow&amp;view_type=form">%s</a>') % (self.id, self.display_name)
        self.message_post(body=_("Rectificative flow created: %s", new_link), subtype_xmlid='mail.mt_note')
        new_flow.message_post(body=_("Created from %s", origin_link), subtype_xmlid='mail.mt_note')

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n.fr.pdp.flow',
            'view_mode': 'form',
            'res_id': new_flow.id,
            'target': 'current',
        }
