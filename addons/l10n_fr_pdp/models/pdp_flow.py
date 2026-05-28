import calendar
import logging
from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError, RedirectWarning
from odoo.fields import Domain

_logger = logging.getLogger(__name__)

PDP_INTERFACE_CODE = 'FFE1025A'
PDP_APP_CODE_QUAL = 'PPF262'  # ODOO raccordement EDI QUAL
PDP_APP_CODE_PROD = 'PDP257'  # ODOO raccordement EDI PROD
# ready ──> sent ┬─> completed
#             ^  └─> error ─┐
#             └─────────────┘
FLOW_OPEN_STATES_SELECTION = [
    ('ready', 'Ready'),
]
FLOW_SENT_STATES_SELECTION = [
    ('error', 'Error'),
    ('sent', 'Sent'),
    ('completed', 'Completed'),
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
    pdp_flow_id = fields.Char(readonly=True)
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
            ('closed', "Closed"),
        ],
        string="Period Status",
        compute='_compute_period_status',
        help="Current status of the reporting period: Open (before grace), Grace (can send), Closed (after deadline).",
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends('company_id', 'period_start', 'period_end', 'report_type', 'operation_type')
    def _compute_move_ids(self):
        # get all the moves for which this is the orignial flow but also all the moves linked to any flow with same scope
        for flow in self:
            flow.move_ids = flow._get_moves()
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

    @api.depends('due_period_start', 'due_period_end')
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

    @api.ondelete(at_uninstall=False)
    def _ondelete_flow(self):
        if any(flow.state in FLOW_SENT_STATES for flow in self):
            raise UserError(self.env._("You cannot delete sent flows."))

    # -------------------------------------------------------------------------
    # Business Methods - Validation
    # -------------------------------------------------------------------------

    @api.model
    def _get_scope_params_for_move(self, move):
        """ This method returns a flow 10 scope dict for a move
        but it DOES NOT verify if move is eligible for flow 10
        """
        report_type = move.l10n_fr_pdp_flow_10_report_type
        transaction = move if report_type == 'transaction' else move._l10n_fr_pdp_get_matched_transactions()[0]
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
    def _get_open_flow_and_create_if_needed(self, move):
        """ This returns a flow that meets the move scope and that is open.
        It creates a new initial flow or a rectificative flow if needed.
        """
        scope_params = self._get_scope_params_for_move(move)
        report_type = scope_params['report_type']
        period_data = self._get_period_flow_properties(move.company_id, move.date, report_type)
        existing_flows = self.search(
            domain=[(key, '=', value) for key, value in scope_params.items()],
            order='id',
        )
        # If last flow is sent, create a new rectificative one.
        is_rectificative = existing_flows and existing_flows[-1].state in FLOW_SENT_STATES

        if not existing_flows or is_rectificative:
            name = ' • '.join([
                f'{period_data["period_start"]} > {period_data["period_end"]}',
                self.env._('Transaction') if report_type == 'transaction' else self.env._('Payment'),
                self.env._('Sale') if scope_params['operation_type'] == 'sale' else self.env._('Purchase'),
                self.env._('Rect.') if is_rectificative else self.env._('Init.'),
            ])
            existing_flows += self.create({
                **scope_params,
                'name': name,
                'due_period_start': period_data['due_period_start'],
                'due_period_end': period_data['due_period_end'],
                'initial_flow_id': existing_flows[0].id if is_rectificative else None,
            })
            existing_flows[-1]._get_moves()._compute_l10n_fr_pdp_last_flow_id()  # update last flow of moves

        return existing_flows[-1]

    # -------------------------------------------------------------------------
    # Business Methods - Payload Building
    # -------------------------------------------------------------------------

    def _build_payload(self, moves=None):
        """Build single XML payload for the entire flow period."""
        invalid_move_states = {None, 'out_of_scope', 'error'}
        for flow in self:
            if flow.state not in FLOW_OPEN_STATES:
                raise UserError(self.env._("Flow %(name)s has already been sent.", name=flow.name))

            if moves is None:
                moves = flow._get_moves()
            valid_moves = moves.filtered(lambda move: move.l10n_fr_pdp_status not in invalid_move_states)

            if not valid_moves:
                flow._message_post_once(self.env._("Payload build failed: no valid invoices."))
                continue

            payload = self.env['pdp.flow.10.xml.builder']._build_payload(flow, valid_moves)
            filename = flow._get_tracking_id() + '.xml'

            if flow.payload_id:
                flow.payload_id.unlink()
            flow.payload_id = self.env['ir.attachment'].create({
                'name': filename,
                'datas': payload,
                'res_model': flow._name,
                'res_id': flow.id,
                'type': 'binary',
                'mimetype': 'application/xml',
            })

            # Log build completion
            error_moves_len = len(valid_moves) < len(moves)
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

    def _get_tracking_id(self):
        self.ensure_one()
        return ''.join([
            f'{self.id:x}',
            self.operation_type[0],
            self.report_type[0],
            "R" if self.initial_flow_id else "I",
            self.period_start.strftime("%y%m%d")
        ]).upper().zfill(19)

    # -------------------------------------------------------------------------
    # Business Methods - Sending
    # -------------------------------------------------------------------------

    def action_send(self, check_totp=True):
        """Send flow payload to transport gateway."""
        auth_totp_disabled = not self.env.user.totp_enabled and not bool(self.env['ir.config_parameter'].sudo().get_param('auth_totp.policy'))
        if check_totp and auth_totp_disabled:
            raise RedirectWarning(
                message=self.env._("To be able to send the report, you need to enable the two-factor authentication."),
                action=self.env.user._get_records_action(
                    target='new',
                    views=[(self.env.ref('base.view_users_form_simple_modif').id, "form")],
                ),
                button_text=self.env._("Go to the Preferences panel"),
            )

        for flow in self:
            if flow.state != 'ready':
                continue

            valid_moves_ids = []
            error_moves_ids = []
            flow_moves = flow._get_moves()
            for move in flow_moves:
                if not move.l10n_fr_pdp_status or move.l10n_fr_pdp_status == 'out_of_scope':
                    continue
                if move.l10n_fr_pdp_status == 'error':
                    error_moves_ids.append(move.id)
                else:
                    valid_moves_ids.append(move.id)

            if flow.initial_flow_id:
                previous_flow = (flow.initial_flow_id + flow.initial_flow_id.rectificative_flow_ids - flow).sorted('id')[-1]
                if previous_flow.state not in FLOW_SENT_STATES:
                    flow._message_post_once(self.env._(
                        "Previous flow %(name)s shoul have been sent.",
                        name=previous_flow.name
                    ))
                    continue
                if set(previous_flow.sent_move_ids.ids) == set(valid_moves_ids):
                    flow._message_post_once(self.env._(
                        "This flow is identical to the previous flow %(name)s.",
                        name=previous_flow.name
                    ))
                    continue
            elif not valid_moves_ids:
                flow._message_post_once(self.env._("No valid transactions/payments to send."))
                continue

            flow._build_payload(flow_moves)

            response = flow._send_to_proxy()
            flow.pdp_flow_id = response['flow_id'].split('_')[-1]
            flow.state = 'sent'

            # Post audit messages on sent moves
            if flow.state in FLOW_SENT_STATES:
                valid_moves = self.env['account.move'].browse(valid_moves_ids)
                flow._post_sent_message_on_moves(valid_moves)
                valid_moves.l10n_fr_pdp_sent_in_flow_ids += flow

            # Log send result
            flow._message_post_once(self.env._(
                "Flow sent: status %(status)s, (message uuid %(transport)s).",
                status=flow.state,
                transport=response['uid'],
            ))

            # create rectificative flow for error moves that must still be send
            if error_moves_ids:
                error_move = self.env['account.move'].browse(error_moves_ids[0])
                self._get_open_flow_and_create_if_needed(error_move)

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
            'ubl': self.payload_id.datas.decode(),
            'external_ref': self._get_tracking_id(),
        }

        result = proxy_user._call_peppol_proxy(
            proxy_user._get_peppol_proxy_endpoint('1/send_document'),
            {'documents': [payload_doc]},
        )
        ppf_messages = result.get('ppf_messages') or []
        if not ppf_messages:
            raise UserError(self.env._("The PDP proxy did not return a flow tracking identifier."))

        proxy_message = ppf_messages[0]
        return {
            'uuid': proxy_message.get('uuid'),
            'flow_id': proxy_message.get('flow_id'),
        }

    # -------------------------------------------------------------------------
    # Business Methods - Deadline Window
    # -------------------------------------------------------------------------

    @api.model
    def _get_period_flow_properties(self, company_id, date, report_type):
        """
        This method returns a dict with start/end dates for the period and due period.
        Where period is the time frame in which the revelvant move are, and the due period
        is the time window in which the report must be send. Sometimes the due period is only one day.
        This depends on the report type and the company perdiodicity.
                               +----------------------------------------------------+-----------------------------------+
                               | transactions flow                                  | payment flow                      |
                               +---------------------+------------------------------+-----------+-----------------------+
                               | period              | due                          | period    | due                   |
        +----------------------+---------------------+------------------------------+-----------+-----------------------+
        | normal_monthly       | Decade:             | 10 days after end of period: | monthly   | 10th of next month    |
        |                      | from day 1 to 10,   | 20th,                        |           |                       |
        |                      | 11 to 20,           | end of month                 |           |                       |
        |                      | 20 to end of month  | 10th of next month           |           |                       |
        +----------------------+---------------------+------------------------------+-----------+-----------------------+
        | normal_quarterly     | monthly             | 10th of next month           | monthly   | 10th of next month    |
        +----------------------+---------------------+------------------------------+-----------+-----------------------+
        | simplified_monthly   | monthly             | between 25th and 30th        | monthly   | between 25th and 30th |
        |                      |                     | of next month                |           | of next month         |
        +----------------------+---------------------+------------------------------+-----------+-----------------------+
        | simplified_bimonthly | bimonthly           | between 25th and 30th        | bimonthly | between 25th and 30th |
        |                      |                     | of next month                |           | of next month         |
        +----------------------+---------------------+------------------------------+-----------+-----------------------+

        """

        def get_monthly_period(date):
            return date.replace(day=1), date.replace(day=last_month_day)

        def get_next_10th_due(date):
            return date.replace(day=10, month=date.month % 12 + 1, year=date.year + (date.month // 12))

        def get_end_of_month_window_after(date):
            month = date.month % 12 + 1
            year = date.year + (date.month // 12)
            return date.replace(
                day=25,
                month=month,
                year=year
            ), date.replace(
                day=min(30, calendar.monthrange(year, month)[1]),
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
                month=period_start.month + 1,
                day=calendar.monthrange(date.year, period_start.month + 1)[1]
            )
            due_period_start, due_period_end = get_end_of_month_window_after(period_end)

        return {
            'period_start': period_start,
            'period_end': period_end,
            'due_period_start': due_period_start,
            'due_period_end': due_period_end,
        }

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

    def _get_moves(self):
        self.ensure_one()
        if self.state in FLOW_SENT_STATES_SELECTION:
            return self.sent_move_ids
        return self.env['account.move'].search_fetch(
                domain=[
                    ('company_id', '=', self.company_id.id),
                    ('date', '>=', self.period_start),
                    ('date', '<=', self.period_end),
                    ('state', '=', 'posted'),
                    ('l10n_fr_pdp_flow_10_report_type', '=', self.report_type),
                    ('l10n_fr_pdp_flow_10_operation_type', '=', self.operation_type),
                ],
                field_names=['l10n_fr_pdp_status'],
                order='id',
            )

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

    def action_view_error_moves(self):
        """Open list view of invalid invoices."""
        action = self._get_moves()._get_records_action(name=self.env._("Invalid Invoices"))
        domain = action.get('domain') or []
        action['domain'] = Domain.AND([domain, [('l10n_fr_pdp_has_error', '=', True)]])
        return action

    def action_open_send_wizard(self):
        """Open send wizard if errors exist, otherwise send directly."""
        self.ensure_one()
        if not self.error_moves_count:
            return self.action_send_from_ui()
        view = self.env.ref('l10n_fr_pdp.l10n_fr_pdp_view_send_wizard_form', raise_if_not_found=False)
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
        return self._get_moves()._get_records_action(
            name=self.env._("Related Invoices"),
            context={'create': False, 'group_by': ['move_type']},
        )

    def action_view_initial(self):
        return self.initial_flow_id._get_records_action()

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
            '|',
            ('initial_flow_id', '!=', None),
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
