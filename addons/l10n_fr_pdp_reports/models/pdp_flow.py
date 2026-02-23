import base64
import calendar
import json
import logging
import re
import uuid

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError, RedirectWarning

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
PDP_FILENAME_ID_LENGTH = 19
# ready ──> sent ┬─> completed
#             ^  └─> error ─┐
#             └─────────────┘
FLOW_OPEN_STATES_SELECTION = [
    ('ready', 'Ready'),
    ('error', 'Error'),
]
FLOW_SENT_STATES_SELECTION = [
    ('sent', 'Sent'),
    ('completed', 'Completed')
]  # once a flow is sent, sent move_id's and xml payload must stay immutable
FLOW_OPEN_STATES = tuple(dict(FLOW_OPEN_STATES_SELECTION))
FLOW_SENT_STATES = tuple(dict(FLOW_SENT_STATES_SELECTION))


class PdpFlow(models.Model):
    _name = 'l10n.fr.pdp.reports.flow'
    _description = 'French PDP Flow'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char()
    state = fields.Selection(
        selection=FLOW_OPEN_STATES_SELECTION + FLOW_SENT_STATES_SELECTION,
        string="Status",
        required=True,
        default='ready',
    )
    payload_id = fields.Many2one('ir.attachment', string="XML Payload", compute='_compute_payload_attachment')
    transport_status = fields.Char(help="Raw status returned by the PDP transport API.")
    transport_message = fields.Text(help="Additional message or error returned by the PDP transport API.")
    report_type = fields.Selection(
        selection=[('transaction', "Transaction"), ('payment', "Payment")],
        required=True,
        default='transaction',
    )
    operation_type = fields.Selection(
        selection=[('sale', "Sales"), ('purchase', "Acquisitions")],
        required=True,
        default='sale',
        help="Defines whether the flow reports sales or acquisition transactions.",
    )
    transmission_type = fields.Selection(
        selection=[('initial', "Initial"), ('rectificative', "Rectificative")],
        help="Type of flow transmission.",
        compute='_compute_transmission_type',
    )
    initial_flow_id = fields.Many2one(comodel_name='l10n.fr.pdp.reports.flow')
    rectificative_flow_ids = fields.One2many(comodel_name='l10n.fr.pdp.reports.flow', inverse_name='initial_flow_id')
    tracking_id = fields.Char(compute='_compute_tracking_id', store=True, readonly=True)  # External tracking identifier sent to the Flow Service.
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    due_period_start = fields.Date(required=True)
    due_period_end = fields.Date(required=True)
    periodicity_code = fields.Char()
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    move_ids = fields.Many2many(
        comodel_name='account.move',
        help="Invoices/Payments reported in this flow.",
        compute='_compute_move_ids',
    )
    sent_move_ids = fields.Many2many(
        comodel_name='account.move',
        relation='sent_account_move__pdp_flow',
        column1='flow_id',
        column2='move_id',
    )
    error_moves_count = fields.Integer(compute='_compute_move_ids')
    error_move_message = fields.Text(string="Invalid Invoice Details")
    period_status = fields.Selection(
        selection=[
            ('open', "Open"),
            ('grace', "Grace"),
            ('closed', "Closed")
        ],
        string="Period Status",
        compute='_compute_period_status',
        help="Current status of the reporting period: Open (before grace), Grace (can send), Closed (after deadline).",
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends('operation_type', 'report_type', 'initial_flow_id', 'period_end')
    def _compute_tracking_id(self):
        for flow in self:
            flow.tracking_id = ''.join([
                f'{flow.id:x}', # this is a sequence -> start with id
                flow.operation_type[0],
                flow.report_type[0],
                "R" if flow.initial_flow_id else "I",
                flow.period_start.strftime("%y%m%d")
            ]).upper().zfill(19)

    @api.depends('company_id', 'period_start', 'period_end', 'report_type', 'operation_type')
    def _compute_move_ids(self):
        # get all the moves for which this is the orignial flow but also all the moves linked to any flow with same scope
        sale_types = self._get_sale_move_types()
        purchase_types = self.env['account.move'].get_purchase_types(False)
        for flow in self:
            # search in loop, but there are few flows, keeping things simplier
            flow.move_ids = self.env['account.move'].search_fetch(
                domain = [
                    ('company_id', '=', flow.company_id.id),
                    ('date', '>=', flow.period_start),
                    ('date', '<=', flow.period_end),
                    ('state', '=', 'posted'),
                    ('l10n_fr_pdp_flow_10_report_type', '=', flow.report_type),
                    ('l10n_fr_pdp_flow_10_operation_type', '=', flow.operation_type),
                ],
                field_names=['l10n_fr_pdp_status'],
                order='id',
            )
            flow.error_moves_count = sum(move.l10n_fr_pdp_status == 'error' for move in flow.move_ids)

    def _compute_payload_attachment(self):
        """Compute the payload attachment record linked to this flow."""
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('mimetype', '=', 'application/xml'),
        ], order='id desc')
        attachments_map = {attachment.res_id: attachment for attachment in attachments}
        for flow in self:
            flow.payload_id = attachments_map.get(flow.id)

    @api.depends('period_end', 'due_period_start', 'due_period_end')
    def _compute_period_status(self):
        """Compute the current status of the reporting period."""
        today = fields.Date.context_today(self)
        for flow in self:
            if today < flow.due_period_start:
                flow.period_status = 'open'
            elif today <= flow.due_period_end:
                flow.period_status = 'grace'
            else:
                flow.period_status = 'closed'

    @api.depends('initial_flow_id')
    def _compute_transmission_type(self):
        for flow in self:
            flow.transmission_type = 'rectificative' if flow.initial_flow_id else 'initial'

    # -------------------------------------------------------------------------
    # CRUD Methods
    # -------------------------------------------------------------------------

    def unlink(self):
        if any(flow.state in FLOW_SENT_STATES for flow in self):
            raise UserError(self.env._("You cannot delete sent flows."))
        return super().unlink()

    # -------------------------------------------------------------------------
    # Business Methods - Validation
    # -------------------------------------------------------------------------

    def _get_sale_move_types(self):
        # overriden in l10n_fr_pdp_pos
        return self.env['account.move'].get_sale_types(True)

    @api.model
    def _get_scope_params_for_move(self, move):
        """ This method returns a flow 10 scope dict for a move
        but it DOES NOT verifiy if move is eligible for flow 10
        """
        if matched_moves := move._l10n_fr_pdp_get_matched_transactions():
            transaction = matched_moves[0]
            report_type = 'payment'
        else:
            transaction = move
            report_type = 'transaction'
        period_data = self._get_period_flow_properties(move.company_id, move.date, report_type)
        operation_type = 'purchase' if transaction._l10n_fr_pdp_is_purchase() else 'sale'
        return {
            'company_id': move.company_id.id,
            'period_start': period_data['period_start'],
            'period_end': period_data['period_end'],
            'operation_type': operation_type,
            'report_type': report_type,
        }

    @api.model
    def _get_last_flow_for_scope(self, scope):
        self.search(
            domain=[(key, '=', value) for key, value in scope.items()],
            order='id desc',
            limit=1,
        )

    @api.model
    def _get_open_flow_and_create_if_needed(self, move):
        """ This returns a flow that meets the move scope and that is open.
        It creates a new initial flow or a rectificative flow if needed.
        """
        scope = self._get_scope_params_for_move(move)
        report_type = scope['report_type']
        period_data = self._get_period_flow_properties(move.company_id, move.date, report_type)
        existing_flows = self.search(
            domain=[(key, '=', value) for key, value in scope.items()],
            order='id',
        )
        # If last flow is sent, create a new rectificative one.
        is_rectificative = existing_flows and existing_flows[-1].state in FLOW_SENT_STATES

        if not existing_flows or is_rectificative:
            name = self.env._(
                '%(date)s - %(report_type)s - %(type)s',
                date=f'{period_data['period_start']} > {period_data['period_end']}',
                report_type='Transaction' if report_type == 'transaction' else 'Payment',
                type='rect.' if is_rectificative else 'init.',
            )
            existing_flows += self.create({
                **scope,
                'name': name,
                'due_period_start': period_data['due_period_start'],
                'due_period_end': period_data['due_period_end'],
                'initial_flow_id': existing_flows[0].id if is_rectificative else None,
            })

        return existing_flows[-1]

    # -------------------------------------------------------------------------
    # Business Methods - Payload Building
    # -------------------------------------------------------------------------

    def _build_payload(self):
        """Build single XML payload for the entire flow period."""
        for flow in self:
            if flow.state not in FLOW_OPEN_STATES:
                raise UserError(_("Flow %(name)s has already been sent.", name=flow.name))

            valid_moves = flow.move_ids.filtered(lambda move: move.l10n_fr_pdp_status not in {'out_of_scope', 'error'})

            if not valid_moves:
                flow._message_post_once(self.env._("Payload build failed: no valid invoices."))
                continue

            payload = self.env['pdp.flow.10.xml.builder']._build_payload(flow, valid_moves)
            filename = flow._build_filename()

            if flow.payload_id:
                flow.payload_id.unlink()
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': payload,
                'res_model': flow._name,
                'res_id': flow.id,
                'type': 'binary',
                'mimetype': 'application/xml',
            })
            flow.payload_id = attachment

            # Log build completion
            error_moves_len = len(valid_moves) < len(flow.move_ids)
            if error_moves_len:
                flow._message_post_once(self.env._(
                    "Payload built with %(valid)s valid invoice(s) and %(invalid)s error(s).",
                    valid=len(valid_moves),
                    invalid=error_moves_len,
                ))
            else:
                flow._message_post_once(self.env._(
                    "Payload built successfully with %(count)s invoice(s).",
                    count=len(valid_moves),
                ))

    # -------------------------------------------------------------------------
    # Business Methods - Sending
    # -------------------------------------------------------------------------

    def action_send(self, check_totp=True):
        """Send flow payload to transport gateway."""
        if check_totp and not self.env.user.totp_enabled:
            raise RedirectWarning(
                message=self.env._("To be able to register, you need to enable the two-factor authentification."),
                action=self.env.user._get_records_action(
                    target='new',
                    views=[(self.env.ref('base.view_users_form_simple_modif').id, "form")]
                ),
                button_text=self.env._("Go to the preference panel"),
            )
        
        for flow in self:
            if flow.state != 'ready':
                continue
            valid_moves = flow.move_ids.filtered(lambda move: move.l10n_fr_pdp_status not in {'out_of_scope', 'error'})
            if flow.initial_flow_id:
                previous_flow = (flow.initial_flow_id + flow.initial_flow_id.rectificative_flow_ids - flow).sorted('id')[-1]
                if previous_flow.state not in FLOW_SENT_STATES:
                    flow._message_post_once(self.env._(
                        "Previous flow %(name)s shoul have been sent.",
                        name=previous_flow.name
                    ))
                    continue
                if previous_flow.sent_move_ids == valid_moves:
                    flow._message_post_once(self.env._(
                        "This flow is identical to the previous flow %(name)s.",
                        name=previous_flow.name
                    ))
                    continue
            elif not valid_moves:
                flow._message_post_once(self.env._("No valid transactions/payments to send."))
                continue

            flow._build_payload()

            response = flow._send_to_proxy()
            flow.state = 'sent'  # TODO check response

            # Post audit messages on sent moves
            if flow.state in FLOW_SENT_STATES:
                flow._post_sent_message_on_moves(valid_moves)
                valid_moves.l10n_fr_pdp_sent_in_flow_ids += flow

            # Log send result
            flow._message_post_once(self.env._(
                "Flow sent: status %(status)s, transport %(transport)s. %(details)s",
                status=flow.state,
                transport=response.get('id') or self.env._("n/a"),
                details=response.get('message') or '',
            ))

        return True

    def _post_sent_message_on_moves(self, moves):
        """Post audit message on successfully sent moves."""
        self.ensure_one()
        flow_link = Markup('<a href="/web#id=%s&amp;model=l10n.fr.pdp.reports.flow&amp;view_type=form">%s</a>') % (self.id, self.name)
        body = self.env._("E-reports %s sent", flow_link)
        for move in moves:
            move.message_post(body=body, subtype_xmlid='mail.mt_note')

    def _get_pdp_proxy_user(self):
        self.ensure_one()
        proxy_user = self.company_id.account_peppol_edi_user
        if not proxy_user:
            raise UserError(self.env._(
                "No active PDP proxy user is configured for company %(company)s.",
                company=self.company_id.display_name,
            ))
        return proxy_user

    def _send_to_proxy(self):
        self.ensure_one()
        if not self.payload_id:
            raise UserError(self.env._("The flow payload is missing. Build the payload before sending."))
        proxy_user = self._get_pdp_proxy_user()
        payload_doc = {
            'flow_number': 10,
            'filename': self.payload_id.name,
            'ubl': self.payload_id.raw.decode(),
            'external_ref': self.tracking_id,
        }

        result = proxy_user._call_peppol_proxy(
            proxy_user._get_peppol_proxy_endpoint('send_document'),
            {'documents': [payload_doc]},
        )
        ppf_messages = result.get('ppf_messages') or []
        if not ppf_messages:
            raise UserError(self.env._("The PDP proxy did not return a flow tracking identifier."))
        
        proxy_message = ppf_messages[0]
        return {
            'id': proxy_message.get('uuid') or proxy_message.get('flow_id'),
            'flow_id': proxy_message.get('flow_id'),
            'status': (proxy_message.get('state') or '').upper() or 'DRAFT',
            'message': result.get('message') or '',
            'acknowledgement': proxy_message.get('acknowledgement') or [],
        }


    # -------------------------------------------------------------------------
    # Business Methods - Deadline Window
    # -------------------------------------------------------------------------

    @api.model
    def _get_period_flow_properties(self, company_id, date, report_type):
        """Return period start/end and due date for a given move date and report type."""

        def get_monthly_period(date):
            return date.replace(day=1), date.replace(day=last_month_day)

        def get_next_10th_due(date):
            return date.replace(day=10, month=(date.month + 1) % 12, year=date.year + (date.month // 12))

        def get_end_of_month_window_after(date):
            month = (date.month + 1) % 12,
            year = date.year + (date.month // 12)
            return date.replace(
                day=25,
                month=month,
                year=year
            ), date.replace(
                day=min(30,calendar.monthrange(year, month)[1]),
                month=month,
                year=year
            )

        last_month_day = calendar.monthrange(date.year, date.month)[1]

        if company_id.l10n_fr_pdp_periodicity == 'normal_monthly':
            if report_type == 'transaction':
                if date.day <= 10:
                    period_start, period_end = date.replace(day=1), date.replace(day=10)
                    due_period_start = due_period_end = date.replace(day=20)
                elif date.day <= 20:
                    period_start, period_end = date.replace(day=11), date.replace(day=20)
                    due_period_start = due_period_end = date.replace(day=last_month_day)
                else:
                    period_start, period_end = date.replace(day=21), date.replace(day=last_month_day)
                    due_period_start = due_period_end = date.replace(day=10, month=(date.month + 1) % 12, year=date.year + (date.month // 12))
            else:
                period_start, period_end = get_monthly_period(date)
                due_period_start = due_period_end = get_next_10th_due(date)
        elif company_id.l10n_fr_pdp_periodicity == 'normal_quarterly':
            period_start, period_end = get_monthly_period(date)
            due_period_start = due_period_end = get_next_10th_due(date)
        elif company_id.l10n_fr_pdp_periodicity == 'simplified_monthly':
            period_start, period_end = get_monthly_period(date)
            due_period_start, due_period_end = get_end_of_month_window_after(period_end)
        else:  # simplified_bimonthly
            period_start = date.replace(month=date.month - (date.month - 1) % 2, day=1)
            period_end = date.replace(
                month=period_start.month+1,
                day=calendar.monthrange(date.year, period_start.month+1)[1]
            )
            due_period_start, due_period_end = get_end_of_month_window_after(period_end)

        return {
            'period_start': period_start,
            'period_end': period_end,
            'due_period_start': due_period_start,
            'due_period_end': due_period_end,
        }

    # -------------------------------------------------------------------------
    # Business Methods 
    # -------------------------------------------------------------------------

    def _build_filename(self):
        """Generate EDI-compliant filename for payload."""
        self.ensure_one()
        app_code = PDP_APP_CODE_QUAL if self.env.company._get_peppol_edi_mode() == 'test' else PDP_APP_CODE_PROD
        return f'{PDP_INTERFACE_CODE}_{app_code}_{app_code}{self.tracking_id}.xml'

    # -------------------------------------------------------------------------
    # Business Methods - Utilities
    # -------------------------------------------------------------------------

    def _message_post_once(self, body, subtype='mail.mt_note'):
        """Post message if it differs from the last one to avoid chatter spam."""
        self.ensure_one()
        last_body = self.message_ids[:1].body if self.message_ids else None
        if last_body == body:
            return
        self.message_post(body=body, subtype_xmlid=subtype)

    def _log_cron_event(self, message):
        """Post message to flow chatter."""
        for flow in self:
            flow._message_post_once(message)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_build_payload_manual(self):
        """Manual trigger for payload building."""
        self._build_payload()
        _logger.info('Manual payload build triggered for flows: %s', self.ids)
        return True

    def action_send_from_ui(self):
        """Send flow from UI with error checking."""
        ctx = dict(self.env.context)
        today = fields.Date.context_today(self)
        for flow in self:
            if flow.error_moves_count and not (ctx.get('ignore_error_invoices') or today == flow.due_period_end):
                raise UserError(self.env._(
                    "This flow still contains invoices with validation errors. "
                    "Fix them or use the 'Send without invalid invoices' button.",
                ))
        _logger.info('Manual transport submission triggered for flows: %s', self.ids)
        return self.with_context(ctx).action_send()


    def _action_open_moves(self, domain, name, context=None):
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
            'domain': domain,
            'name': name,
            'context': context or {},
        }

    def action_view_error_moves(self):
        """Open list view of invalid invoices."""
        return self._action_open_moves(
            [
                ('id', 'in', self.move_ids.ids),
                ('l10n_fr_pdp_status', '=', 'error')
            ],
            self.env._("Invalid Invoices"),
        )

    def action_open_send_wizard(self):
        """Open send wizard if errors exist, otherwise send directly."""
        self.ensure_one()
        if not self.error_moves_count:
            return self.action_send_from_ui()
        view = self.env.ref('l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_send_wizard_form', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n.fr.pdp.reports.send.wizard',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'target': 'new',
            'context': {'default_flow_id': self.id},
        }

    def action_view_moves(self):
        """Open list view of related invoices."""
        return self._action_open_moves(
            [('id', 'in', self.move_ids.ids)],
            self.env._("Related Invoices"),
            {'create': False, 'group_by': ['move_type']},
        )

    def action_view_initial(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.initial_flow_id.id,
        }

    # -------------------------------------------------------------------------
    # Cron
    # -------------------------------------------------------------------------

    def _cron_update_and_send_flows(self):
        companies = self.env['res.company'].search([
            ('l10n_fr_f10_enable_reporting', '=', True),
        ])
        for company in companies:
            _logger.info('Running PDP flow handler cron for company %s', company.id)
            try:
                self._cron_process_company(company)
            except Exception:
                _logger.exception('Failed to handle PDP flows for company %s', company.id)

    def _cron_process_company(self, company):
        today = fields.Date.today()
        sudo_ready_flows = self.sudo().search([
            ('company_id', '=', company.id),
            ('state', '=', 'ready'),
            ('due_period_start', '>=', today),
            ('due_period_end', '<=', today),
        ])
        for flow in sudo_ready_flows:
            try:
                if flow.transmission_type == 'initial':
                    if today < flow.due_period_start:
                        continue
                    if flow.error_moves_count and today < flow.due_period_end:
                        continue
                else:
                    # RE flows: send immediately when ready (no deadline constraint)
                    if flow.state != 'ready' or flow.error_moves_count:
                        continue
                flow.with_company(flow.company_id).sudo().action_send(check_totp=False)
                flow._log_cron_event(
                    self.env._("Flow automatically sent by cron (status: %(status)s). %(extra)s",
                      status=flow.transport_status or flow.state,
                      extra=self.env._("Invalid invoices were excluded.") if flow.error_moves_count else ""),
                )
            except Exception:
                _logger.exception('Failed to send Flow 10 %s', flow.name)