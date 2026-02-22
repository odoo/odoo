import calendar
import logging
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models, _

_logger = logging.getLogger(__name__)


class PdpFlowAggregator(models.AbstractModel):
    _name = 'l10n.fr.pdp.flow.aggregator'
    _description = 'PDP Flow Aggregator'

    _OPEN_STATES = {'pending', 'building', 'ready', 'error'}
    _SENT_STATES = {'sent', 'completed'}

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @api.model
    def _cron_generate_daily_flows(self):
        """Cron job to generate PDP flows for all enabled companies."""
        companies = self.env['res.company'].search([('l10n_fr_pdp_enabled', '=', True)])
        for company in companies:
            _logger.info('Running PDP flow aggregation cron for company %s', company.id)
            try:
                self.sudo().with_company(company)._cron_process_company(company)
            except Exception:
                _logger.exception('Failed to generate PDP flows for company %s', company.id)

    def _cron_process_company(self, company):
        """Process unprocessed moves for a single company."""
        today = fields.Date.context_today(self)
        moves = self._get_unprocessed_moves(company)
        flows = self.env['l10n.fr.pdp.flow'].browse()
        if moves:
            _logger.info('Processing %s unreported invoices for company %s', len(moves), company.id)
            flows |= self._aggregate_moves(moves)
        else:
            _logger.debug('No new PDP invoices to process for company %s', company.id)

        # Always ensure payment flows stay in sync for the current payment window.
        payment_flows, payment_rebuild = self._synchronize_payment_flows(company.id, today, company.currency_id.id)
        if payment_rebuild:
            payment_rebuild._build_payload()
            payment_rebuild._log_cron_event(_("Payment flow payload rebuilt automatically by the PDP cron."))
        flows |= payment_flows | payment_rebuild
        # Build any flows needing a (re)build.
        pending_flows = self.env['l10n.fr.pdp.flow'].search([
            ('company_id', '=', company.id),
            ('state', 'in', ('pending', 'building', 'error')),
        ]) - flows

        # Rebuild pending flows only once the reporting period is over (grace/closed).
        def _is_period_over(flow):
            period_end = fields.Date.to_date(flow.period_end or flow.reporting_date)
            return bool(period_end) and today > period_end

        pending_flows = pending_flows.filtered(_is_period_over)
        if pending_flows:
            pending_flows._build_payload()
            pending_flows._log_cron_event(_("Flow payload rebuilt automatically by the PDP cron."))
        return flows

    # -------------------------------------------------------------------------
    # Move Discovery
    # -------------------------------------------------------------------------

    def _get_unprocessed_moves(self, company):
        """Find invoices eligible for PDP reporting that haven't been reported yet.

        A move is considered reported only when it is included in at least one
        sent/completed flow payload (i.e., present in the flow but not in
        `error_move_ids` for that sent flow).
        """
        Move = self.env['account.move']
        sale_types = Move.get_sale_types(include_receipts=True)
        purchase_types = Move.get_purchase_types(include_receipts=False)
        domain = [
            ('company_id', '=', company.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', sale_types + purchase_types),
        ]
        moves = Move.search(domain, order='invoice_date, id')
        eligible = self.env['account.move'].browse()
        skipped = []
        for move in moves:
            if move.move_type in sale_types:
                if move._get_l10n_fr_pdp_transaction_type():
                    eligible |= move
                else:
                    skipped.append(move.display_name)
            else:
                # Acquisitions: only B2B international are in scope.
                if self._is_international_partner(move):
                    eligible |= move
                else:
                    skipped.append(move.display_name)
        if skipped:
            preview = ', '.join(skipped[:10])
            if len(skipped) > 10:
                preview += ', ...'
            _logger.info('Skipping %s invoices outside PDP scope for company %s: %s', len(skipped), company.id, preview)

        def _is_reported(move):
            sent_flows = move.l10n_fr_pdp_flow_ids.filtered(lambda f: f.state in self._SENT_STATES)
            return bool(sent_flows) and any(move not in f.error_move_ids for f in sent_flows)

        return eligible.filtered(lambda m: not _is_reported(m))

    # -------------------------------------------------------------------------
    # Aggregation
    # -------------------------------------------------------------------------

    def _aggregate_moves(self, moves):
        """Aggregate moves into PDP flows by period, currency, and transaction type."""
        if not moves:
            return self.env['l10n.fr.pdp.flow'].browse()
        grouped = self._group_moves(moves)
        flow_model = self.env['l10n.fr.pdp.flow']
        aggregated_flows = flow_model.browse()
        payment_source_cache = {}
        for key, group_moves in grouped.items():
            company_id, period_start, period_end, periodicity_code, currency_id, operation_type = key

            period_moves = self._get_transaction_period_moves(
                company_id, period_start, period_end, currency_id, operation_type,
            )
            period_moves |= group_moves
            transaction_type = 'international' if operation_type == 'purchase' else self._describe_transaction_scope(period_moves)
            if not transaction_type:
                continue

            flows_for_key, rebuild_flows = self._synchronize_flows_for_group(
                company_id,
                period_start,
                period_end,
                periodicity_code,
                currency_id,
                transaction_type,
                period_moves,
                operation_type,
            )

            # Create/update the payment flow for the same period anchor (sales only).
            payment_flow = flow_model.browse()
            payment_rebuild = flow_model.browse()
            if operation_type == 'sale':
                payment_period_start, payment_period_end, _payment_periodicity_code = self._get_period_bounds(
                    company_id, period_start, 'payment',
                )
                cache_key = (company_id, payment_period_start, payment_period_end)
                if cache_key not in payment_source_cache:
                    payment_source_cache[cache_key] = self._get_payment_source_moves(
                        company_id, payment_period_start, payment_period_end,
                    )
                payment_source_moves = payment_source_cache[cache_key]
                payment_flow, payment_rebuild = self._synchronize_payment_flows(
                    company_id,
                    period_start,
                    currency_id,
                    payment_source_moves=payment_source_moves,
                )

                rebuild_flows |= payment_rebuild
            if rebuild_flows:
                rebuild_flows._build_payload()
                rebuild_flows._log_cron_event(_("Flow payload rebuilt automatically by the PDP cron."))
            aggregated_flows |= flows_for_key | payment_flow
        return aggregated_flows

    def _get_transaction_period_moves(self, company_id, period_start, period_end, currency_id, operation_type):
        """Return all eligible transaction moves for a period (full dataset)."""
        Move = self.env['account.move']
        sale_types = Move.get_sale_types(include_receipts=True)
        purchase_types = Move.get_purchase_types(include_receipts=False)
        move_types = sale_types if operation_type == 'sale' else purchase_types
        domain = [
            ('company_id', '=', company_id),
            ('state', '=', 'posted'),
            ('move_type', 'in', move_types),
            ('currency_id', '=', currency_id),
            '|',
            '&', ('invoice_date', '=', False), ('date', '>=', period_start), ('date', '<=', period_end),
            '&', ('invoice_date', '!=', False), ('invoice_date', '>=', period_start), ('invoice_date', '<=', period_end),
        ]
        candidates = Move.search(domain, order='invoice_date, id')
        if operation_type == 'sale':
            return candidates.filtered(lambda m: bool(m._get_l10n_fr_pdp_transaction_type()))
        return candidates.filtered(self._is_international_partner)

    def _is_international_partner(self, move):
        """Return True when a purchase move is in international e-reporting scope."""
        return move._is_international_partner_for_purchase()

    def _group_moves(self, moves):
        """Group moves by (company, period, currency)."""
        grouped = defaultdict(self.env['account.move'].browse)
        for move in moves:
            move_date = move.invoice_date or move.date
            operation_type = 'sale' if move.is_sale_document(include_receipts=True) else 'purchase'
            period_start, period_end, periodicity_code = self._get_period_bounds(
                move.company_id.id, move_date, 'transaction',
            )
            key = (move.company_id.id, period_start, period_end, periodicity_code, move.currency_id.id, operation_type)
            grouped[key] |= move
        return grouped

    def _describe_transaction_scope(self, moves):
        """Determine transaction scope from moves (b2c, international, or mixed)."""
        has_b2c = False
        has_international = False
        for move in moves:
            tx_type = move._get_l10n_fr_pdp_transaction_type()
            if tx_type == 'b2c':
                has_b2c = True
            elif tx_type == 'international':
                has_international = True
        if has_b2c and has_international:
            return 'mixed'
        if has_international:
            return 'international'
        if has_b2c:
            return 'b2c'
        return False

    # -------------------------------------------------------------------------
    # Period Calculation
    # -------------------------------------------------------------------------

    def _get_period_bounds(self, company_id, reporting_date, report_kind):
        """Calculate period start/end based on company periodicity settings."""
        company = self.env['res.company'].browse(company_id)
        base_date = fields.Date.to_date(reporting_date)
        periodicity = (
            company.l10n_fr_pdp_payment_periodicity if report_kind == 'payment'
            else company.l10n_fr_pdp_periodicity
        ) or ('monthly' if report_kind == 'payment' else 'decade')

        if periodicity == 'monthly':
            period_start = base_date.replace(day=1)
            period_end = (period_start + relativedelta(months=1)) - relativedelta(days=1)
            return period_start, period_end, 'M'  # M = monthly period code (Flux 10)

        if periodicity == 'bimonthly':
            period_start = base_date.replace(day=1)
            if base_date.month % 2 == 0:
                period_start = (period_start - relativedelta(months=1)).replace(day=1)
            period_end = (period_start + relativedelta(months=2)) - relativedelta(days=1)
            return period_start, period_end, 'B'  # B = bimonthly period code

        if periodicity == 'quarterly':
            quarter_month = ((base_date.month - 1) // 3) * 3 + 1
            period_start = base_date.replace(month=quarter_month, day=1)
            period_end = (period_start + relativedelta(months=3)) - relativedelta(days=1)
            return period_start, period_end, 'T'  # T = trimestre

        # Decade (default)
        day = base_date.day
        if day <= 10:
            start_day, end_day = 1, 10
        elif day <= 20:
            start_day, end_day = 11, 20
        else:
            start_day = 21
            end_day = calendar.monthrange(base_date.year, base_date.month)[1]
        return base_date.replace(day=start_day), base_date.replace(day=end_day), 'D'  # D = decadal window (1-10 / 11-20 / 21-end)

    # -------------------------------------------------------------------------
    # Flow Synchronization
    # -------------------------------------------------------------------------

    def _synchronize_flow_for_domain(
        self,
        *,
        domain,
        create_values,
        moves,
        transaction_type,
        period_end,
        unlink_if_empty=False,
        skip_if_last_sent_same_moves=False,
    ):
        """Create or update a single flow matching the given domain.

        This keeps at most one open flow per domain and determines whether it
        should be an initial (IN) or rectificative (RE) flow based on existing
        sent flows.

        Args:
            domain: Domain identifying a unique flow scope (period/currency/kind).
            create_values: Base values for creating a flow (without transmission/is_correction/move_ids).
            moves: Moves to include in the flow.
            transaction_type: Computed scope for the flow (b2c/international/mixed).
            period_end: Period end used to decide when to rebuild pending flows.
            unlink_if_empty: If True, remove any open flow when no moves are found.
            skip_if_last_sent_same_moves: If True, avoid creating a new RE flow when the last sent one matches.
        """
        flow_model = self.env['l10n.fr.pdp.flow']
        existing_flows = flow_model.search(domain, order='create_date desc')
        sent_flows = existing_flows.filtered(lambda f: f.state in self._SENT_STATES)
        open_flows = existing_flows.filtered(lambda f: f.state in self._OPEN_STATES)

        want_correction = bool(sent_flows)
        target_transmission = 'RE' if want_correction else 'IN'

        target_open_flows = open_flows.filtered(
            lambda f: f.transmission_type == target_transmission and bool(f.is_correction) == want_correction,
        )
        obsolete_open_flows = open_flows - target_open_flows
        if obsolete_open_flows:
            obsolete_open_flows.unlink()

        flow = target_open_flows[:1]
        extra_open_flows = target_open_flows - flow
        if extra_open_flows:
            extra_open_flows.unlink()

        if unlink_if_empty and not moves:
            if flow:
                flow.unlink()
            return flow_model.browse(), flow_model.browse()

        if skip_if_last_sent_same_moves and want_correction and not flow and moves:
            last_sent = sent_flows.sorted('create_date')[-1:]
            if last_sent and moves.sorted('id') == last_sent.move_ids.sorted('id'):
                return last_sent, flow_model.browse()

        changed = False
        if flow:
            changed = flow._synchronize_moves(moves)
        else:
            flow = flow_model.create({
                **create_values,
                'transaction_type': transaction_type,
                'transmission_type': target_transmission,
                'is_correction': want_correction,
                'move_ids': [Command.set(moves.ids)],
            })
            flow._update_reference_name()
            flow._ensure_tracking_id()
            changed = True

        if flow.transaction_type != transaction_type:
            flow.transaction_type = transaction_type

        rebuild_flows = flow_model.browse()
        today = fields.Date.context_today(self)
        if changed or not flow.has_payload or (flow.state == 'pending' and today > period_end):
            rebuild_flows |= flow
        return flow, rebuild_flows

    def _synchronize_flows_for_group(
        self,
        company_id,
        period_start,
        period_end,
        periodicity_code,
        currency_id,
        transaction_type,
        period_moves,
        operation_type,
    ):
        """Create or update the transaction flow for a period (full dataset)."""
        base_domain = [
            ('company_id', '=', company_id),
            ('currency_id', '=', currency_id),
            ('flow_type', '=', 'transaction_report'),
        ]

        domain = base_domain + [
            ('report_kind', '=', 'transaction'),
            ('operation_type', '=', operation_type),
            ('period_start', '=', period_start),
            ('period_end', '=', period_end),
            ('periodicity_code', '=', periodicity_code),
        ]
        flow, rebuild_flows = self._synchronize_flow_for_domain(
            domain=domain,
            create_values={
                'company_id': company_id,
                'reporting_date': period_start,
                'currency_id': currency_id,
                'document_type': 'mixed',
                'flow_type': 'transaction_report',
                'report_kind': 'transaction',
                'operation_type': operation_type,
                'period_start': period_start,
                'period_end': period_end,
                'periodicity_code': periodicity_code,
                'issue_datetime': fields.Datetime.now(),
            },
            moves=period_moves,
            transaction_type=transaction_type,
            period_end=period_end,
        )

        _logger.debug(
            'PDP Flow synchronized: company=%s period=%s-%s currency=%s scope=%s operation=%s flow=%s moves=%s',
            company_id, period_start, period_end, currency_id, transaction_type, operation_type, flow.id, period_moves.ids,
        )
        return flow, rebuild_flows

    def _synchronize_payment_flows(self, company_id, anchor_date, currency_id, payment_source_moves=None):
        """Create or update the payment flow for the payment period (full dataset)."""
        payment_period_start, payment_period_end, payment_periodicity_code = self._get_period_bounds(company_id, anchor_date, 'payment')
        if payment_source_moves is None:
            payment_source_moves = self._get_payment_source_moves(company_id, payment_period_start, payment_period_end)
        payment_moves = self._get_payment_moves(payment_source_moves).filtered(
            lambda m: m.currency_id.id == currency_id and bool(m._get_l10n_fr_pdp_transaction_type()),
        )
        payment_transaction_type = self._describe_transaction_scope(payment_moves) or 'mixed'
        base_domain = [
            ('company_id', '=', company_id),
            ('currency_id', '=', currency_id),
            ('flow_type', '=', 'transaction_report'),
        ]
        payment_domain = base_domain + [
            ('report_kind', '=', 'payment'),
            ('period_start', '=', payment_period_start),
            ('period_end', '=', payment_period_end),
            ('periodicity_code', '=', payment_periodicity_code),
        ]
        return self._synchronize_flow_for_domain(
            domain=payment_domain,
            create_values={
                'company_id': company_id,
                'reporting_date': payment_period_start,
                'currency_id': currency_id,
                'document_type': 'sale',
                'flow_type': 'transaction_report',
                'report_kind': 'payment',
                'period_start': payment_period_start,
                'period_end': payment_period_end,
                'periodicity_code': payment_periodicity_code,
                'issue_datetime': fields.Datetime.now(),
            },
            moves=payment_moves,
            transaction_type=payment_transaction_type,
            period_end=payment_period_end,
            unlink_if_empty=True,
            skip_if_last_sent_same_moves=True,
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_payment_moves(self, moves):
        """Return moves considered as payments for the flow."""
        result = self.env['account.move'].browse()
        for move in moves:
            transaction_type = move._get_l10n_fr_pdp_transaction_type()
            is_advance = self._is_advance_payment_move(move)
            has_reportable_lines = is_advance or any(
                self._is_service_payment_line(line)
                for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            )

            if transaction_type == 'b2c':
                # Payments are reported only for services (bloc 10.4).
                # Exception: advance invoices (BT-3 386/500) are always reported.
                if not has_reportable_lines:
                    continue
                result |= move
                continue

            if transaction_type == 'international':
                # Payments are reported only for services with French VAT (bloc 10.2).
                # Exception: advance invoices (BT-3 386/500) are always reported.
                if not has_reportable_lines:
                    continue
                if move.amount_tax <= 0:
                    continue

            result |= move
        return result

    def _is_advance_payment_move(self, move):
        """Return True when payment reporting must include all lines (advance invoices)."""
        bt3_code = (move.l10n_fr_pdp_bt3_code or '').strip()
        if bt3_code in {'386', '500'}:
            return True
        lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        return any('is_downpayment' in line._fields and line.is_downpayment for line in lines)

    def _is_service_payment_line(self, line):
        """Return True when a line should be considered in payment reporting.

        Services with option débits (tax_exigibility='on_invoice') are excluded
        because TVA is already due at invoicing — no payment reporting needed.
        """
        taxes = line.tax_ids
        if line.product_id:
            is_service = line.product_id.type == 'service' or any(t.tax_scope == 'service' for t in taxes)
        else:
            is_service = any(
                (t.l10n_fr_pdp_tt81_category or '').strip() == 'TPS1' or t.tax_scope == 'service'
                for t in taxes
            )
        if not is_service:
            return False
        # Only report payments for services with TVA à l'encaissement (on_payment)
        return any(t.tax_exigibility == 'on_payment' for t in taxes) if taxes else True

    def _is_payment_partial_aml(self, aml):
        """Return True when a reconciled AML corresponds to an actual payment."""
        move = aml.move_id
        has_origin_payment = 'origin_payment_id' in move._fields and bool(move.origin_payment_id)
        has_statement_line = 'statement_line_id' in move._fields and bool(move.statement_line_id)
        return has_origin_payment or has_statement_line

    def _get_payment_source_moves(self, company_id, period_start, period_end):
        """Sale docs with payments dated in the payment window."""
        sale_types = self.env['account.move'].get_sale_types(include_receipts=True)
        candidates = self.env['account.move'].search([
            ('company_id', '=', company_id),
            ('state', '=', 'posted'),
            ('move_type', 'in', sale_types),
        ], order='invoice_date, id')
        result = self.env['account.move'].browse()
        for move in candidates:
            # Cash receipt acts as its own payment.
            pay_date = move.invoice_date or move.date
            if move.move_type == 'out_receipt' and period_start <= pay_date <= period_end:
                result |= move
                continue
            # Find reconciled payment lines dated in the window.
            for partial in move._get_all_reconciled_invoice_partials():
                if aml := partial.get('aml'):
                    if not self._is_payment_partial_aml(aml):
                        continue
                    if period_start <= aml.date <= period_end:
                        result |= move
                        break
        # Include invoices that have pending unreconcile events in the period.
        event_moves = self.env['l10n.fr.pdp.payment.event'].sudo().search([
            ('company_id', '=', company_id),
            ('state', '=', 'pending'),
            ('event_date', '>=', period_start),
            ('event_date', '<=', period_end),
        ]).mapped('move_id')
        result |= event_moves.filtered(
            lambda m: m.state == 'posted' and m.move_type in sale_types
        )
        return result

    def _split_batches(self, moves):
        """Split moves into batches if exceeding max per flow."""
        company = moves.company_id[:1]
        max_per_flow = self._get_max_moves_per_flow(company)
        if max_per_flow <= 0 or len(moves) <= max_per_flow:
            return [moves]
        return [moves[start:start + max_per_flow] for start in range(0, len(moves), max_per_flow)]

    def _get_max_moves_per_flow(self, company):
        """Return max invoices per flow (configurable)."""
        return 10000
