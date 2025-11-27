import calendar
import logging
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo import Command, _, api, fields, models

_logger = logging.getLogger(__name__)


class PdpFlowAggregator(models.AbstractModel):
    _name = 'l10n.fr.pdp.flow.aggregator'
    _description = 'PDP Flow Aggregator'

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @api.model
    def _cron_generate_daily_flows(self):
        """Cron job to generate PDP flows for all enabled companies."""
        companies = self.env["res.company"].search([("l10n_fr_pdp_enabled", "=", True)])
        for company in companies:
            _logger.info("Running PDP flow aggregation cron for company %s", company.id)
            try:
                self.sudo().with_company(company)._cron_process_company(company)
            except Exception:
                _logger.exception("Failed to generate PDP flows for company %s", company.id)

    def _cron_process_company(self, company):
        """Process unprocessed moves for a single company."""
        moves = self._get_unprocessed_moves(company)
        flows = self.env["l10n.fr.pdp.flow"].browse()
        if moves:
            _logger.info("Processing %s unreported invoices for company %s", len(moves), company.id)
            flows |= self._aggregate_moves(moves)
        else:
            _logger.debug("No new PDP invoices to process for company %s", company.id)

        # Always ensure payment flows stay in sync for the current payment window.
        today = fields.Date.context_today(self)
        pay_start, pay_end, _pay_code = self._get_period_bounds(company.id, today, "payment")
        payment_source_moves = self._get_payment_source_moves(company.id, pay_start, pay_end)
        if payment_source_moves or self.env["l10n.fr.pdp.flow"].search_count([
            ("company_id", "=", company.id),
            ("report_kind", "=", "payment"),
            ("period_start", "=", pay_start),
            ("period_end", "=", pay_end),
        ]):
            payment_flows, payment_rebuild = self._synchronize_payment_flows(
                company.id,
                pay_start,
                company.currency_id.id,
                "mixed",
                payment_source_moves,
                self.env["l10n.fr.pdp.flow"].browse(),
            )
            if payment_rebuild:
                payment_rebuild._build_payload()
                payment_rebuild._log_cron_event(_("Payment flow payload rebuilt automatically by the PDP cron."))
            flows |= payment_flows | payment_rebuild
        # Build any pending flows (IN/CO/MO/RE) left in draft/building/error.
        processed_ids = flows.ids
        pending_flows = self.env["l10n.fr.pdp.flow"].search([
            ("company_id", "=", company.id),
            ("state", "in", ("draft", "building", "error")),
        ]).filtered(lambda f: f.id not in processed_ids)
        if pending_flows:
            pending_flows._build_payload()
            pending_flows._log_cron_event(_("Flow payload rebuilt automatically by the PDP cron."))
        return flows

    # -------------------------------------------------------------------------
    # Move Discovery
    # -------------------------------------------------------------------------

    def _get_unprocessed_moves(self, company):
        """Find invoices eligible for PDP reporting that haven't been sent."""
        domain = [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("move_type", "in", ("out_invoice", "out_refund", "out_receipt")),
        ]
        moves = self.env["account.move"].search(domain, order="invoice_date, id")
        eligible = self.env["account.move"].browse()
        skipped = []
        for move in moves:
            if move._get_l10n_fr_pdp_transaction_type():
                eligible |= move
            else:
                skipped.append(move.display_name)
        if skipped:
            preview = ", ".join(skipped[:10])
            if len(skipped) > 10:
                preview += ", …"
            _logger.info("Skipping %s invoices outside PDP scope for company %s: %s", len(skipped), company.id, preview)
        # Filter out moves already in sent/done flows
        return eligible.filtered(
            lambda m: not any(s in {'pending', 'done'} for s in m.l10n_fr_pdp_flow_ids.mapped('state')),
        )

    # -------------------------------------------------------------------------
    # Aggregation
    # -------------------------------------------------------------------------

    def _aggregate_moves(self, moves):
        """Aggregate moves into PDP flows by period, currency, and transaction type."""
        if not moves:
            return self.env["l10n.fr.pdp.flow"].browse()
        grouped = self._group_moves(moves)
        flow_model = self.env["l10n.fr.pdp.flow"]
        aggregated_flows = flow_model.browse()
        for key, group_moves in grouped.items():
            company_id, period_start, period_end, periodicity_code, currency_id = key
            transaction_type = self._describe_transaction_scope(group_moves)
            if not transaction_type:
                continue
            flows_for_key, rebuild_flows = self._synchronize_flows_for_group(
                company_id, period_start, period_end, periodicity_code, currency_id, transaction_type, group_moves,
            )
            if rebuild_flows:
                rebuild_flows._build_payload()
                rebuild_flows._log_cron_event(_("Flow payload rebuilt automatically by the PDP cron."))
            aggregated_flows |= flows_for_key
        return aggregated_flows

    def _group_moves(self, moves):
        """Group moves by (company, period, currency)."""
        grouped = defaultdict(self.env["account.move"].browse)
        for move in moves:
            move_date = move.invoice_date or move.date
            period_start, period_end, periodicity_code = self._get_period_bounds(
                move.company_id.id, move_date, "transaction",
            )
            key = (move.company_id.id, period_start, period_end, periodicity_code, move.currency_id.id)
            grouped[key] |= move
        return grouped

    def _describe_transaction_scope(self, moves):
        """Determine transaction scope from moves (b2c, international, or mixed)."""
        has_b2c = False
        has_international = False
        for move in moves:
            tx_type = move._get_l10n_fr_pdp_transaction_type()
            if tx_type == "b2c":
                has_b2c = True
            elif tx_type == "international":
                has_international = True
        if has_b2c and has_international:
            return "mixed"
        if has_international:
            return "international"
        if has_b2c:
            return "b2c"
        return False

    # -------------------------------------------------------------------------
    # Period Calculation
    # -------------------------------------------------------------------------

    def _get_period_bounds(self, company_id, reporting_date, report_kind):
        """Calculate period start/end based on company periodicity settings."""
        company = self.env["res.company"].browse(company_id)
        base_date = fields.Date.to_date(reporting_date)
        periodicity = (
            company.l10n_fr_pdp_payment_periodicity if report_kind == "payment"
            else company.l10n_fr_pdp_periodicity
        ) or ("monthly" if report_kind == "payment" else "decade")

        if periodicity == "monthly":
            period_start = base_date.replace(day=1)
            period_end = (period_start + relativedelta(months=1)) - relativedelta(days=1)
            return period_start, period_end, "M"  # M = monthly period code (Flux 10)

        if periodicity == "bimonthly":
            period_start = base_date.replace(day=1)
            if base_date.month % 2 == 0:
                period_start = (period_start - relativedelta(months=1)).replace(day=1)
            period_end = (period_start + relativedelta(months=2)) - relativedelta(days=1)
            return period_start, period_end, "B"  # B = bimonthly period code

        # Decade (default)
        day = base_date.day
        if day <= 10:
            start_day, end_day = 1, 10
        elif day <= 20:
            start_day, end_day = 11, 20
        else:
            start_day = 21
            end_day = calendar.monthrange(base_date.year, base_date.month)[1]
        return base_date.replace(day=start_day), base_date.replace(day=end_day), "D"  # D = decadal window (1-10 / 11-20 / 21-end)

    # -------------------------------------------------------------------------
    # Flow Synchronization
    # -------------------------------------------------------------------------

    def _synchronize_flows_for_group(self, company_id, period_start, period_end, periodicity_code, currency_id, transaction_type, group_moves):
        """Create or update flows for a group of moves."""
        flow_model = self.env["l10n.fr.pdp.flow"]
        open_states = {'draft', 'building', 'ready', 'error'}
        base_domain = [
            ("company_id", "=", company_id),
            ("currency_id", "=", currency_id),
            ("flow_type", "=", 'transaction_report'),
        ]

        # Transaction flows
        domain = base_domain + [
            ("report_kind", "=", "transaction"),
            ("period_start", "=", period_start),
            ("period_end", "=", period_end),
            ("periodicity_code", "=", periodicity_code),
        ]
        existing_flows = flow_model.search(domain + [("is_correction", "=", False)], order="create_date asc")
        draft_flows = existing_flows.filtered(lambda f: f.state in open_states and not f.is_correction)
        closed_flows = existing_flows - draft_flows

        rebuild_flows = flow_model.browse()
        resulting_flows = flow_model.browse()
        batches = list(self._split_batches(group_moves))
        reference_flow = closed_flows.sorted("create_date")[-1] if closed_flows else flow_model.browse()

        for batch_moves in batches:
            is_new_flow = False
            if draft_flows:
                flow = draft_flows[0]
                changed = flow._synchronize_moves(batch_moves)
                draft_flows = draft_flows - flow
            else:
                transmission_type = "CO" if existing_flows else "IN"
                flow = flow_model.create({
                    "company_id": company_id,
                    "reporting_date": period_start,
                    "currency_id": currency_id,
                    "document_type": "mixed",
                    "flow_type": 'transaction_report',
                    "transaction_type": transaction_type,
                    "report_kind": "transaction",
                    "transmission_type": transmission_type,
                    "is_correction": False,
                    "transmission_reference": False,
                    "transmission_reference_type": False,
                    "period_start": period_start,
                    "period_end": period_end,
                    "periodicity_code": periodicity_code,
                    "issue_datetime": fields.Datetime.now(),
                    "move_ids": [Command.set(batch_moves.ids)],
                })
                flow._reset_slices(batch_moves)
                flow._update_reference_name()
                flow._ensure_tracking_id()
                changed = True
                is_new_flow = True
                existing_flows |= flow

            # Update flow attributes (transmission type logic)
            has_previous = bool(existing_flows.filtered(lambda rec: rec.id != flow.id))
            updates = {}

            if closed_flows and reference_flow:
                if set(batch_moves.ids) == set(reference_flow.move_ids.ids):
                    # No change vs sent flow -> skip
                    continue
                if batch_moves & reference_flow.move_ids:
                    updates["transmission_type"] = "MO"
                    updates["is_correction"] = True
                    updates["transmission_reference"] = reference_flow.transport_identifier or False
                    updates["transmission_reference_type"] = reference_flow.transmission_type or "IN"
                else:
                    updates["transmission_type"] = "CO" if has_previous else "IN"
                    updates["is_correction"] = False
                    updates["transmission_reference"] = False
                    updates["transmission_reference_type"] = False
            elif not is_new_flow:
                # Only update transmission_type for existing flows
                updates["transmission_type"] = "IN" if not has_previous else "CO"

            # For existing flows, update period and other attributes
            if not is_new_flow:
                updates.update({
                    "reporting_date": period_start,
                    "period_start": period_start,
                    "period_end": period_end,
                    "periodicity_code": periodicity_code,
                    "report_kind": "transaction",
                    "document_type": "mixed",
                })

            if updates:
                flow.write(updates)
                if not is_new_flow:
                    flow._update_reference_name()
                    flow._ensure_tracking_id()

            if flow.state not in open_states:
                flow.state = "draft"
            if flow.transaction_type != transaction_type:
                flow.transaction_type = transaction_type
            if changed or not flow.has_payload:
                rebuild_flows |= flow
            resulting_flows |= flow
            _logger.debug(
                "PDP Flow aggregated: company=%s period=%s-%s currency=%s scope=%s flow=%s moves=%s",
                company_id, period_start, period_end, currency_id, transaction_type, flow.id, batch_moves.ids,
            )

        # Clean up unused draft flows
        if draft_flows:
            draft_flows._synchronize_moves(self.env["account.move"].browse())
            draft_flows.unlink()

        # Payment flows
        payment_flows, payment_rebuild = self._synchronize_payment_flows(
            company_id, period_start, currency_id, transaction_type, group_moves,
            reference_flow or resulting_flows.sorted("create_date")[-1:],
        )
        rebuild_flows |= payment_rebuild
        resulting_flows |= payment_flows

        return resulting_flows, rebuild_flows

    def _synchronize_payment_flows(self, company_id, period_start, currency_id, transaction_type, group_moves, reference_flow):
        """Create or update payment flows for the period."""
        flow_model = self.env["l10n.fr.pdp.flow"]
        open_states = {'draft', 'building', 'ready', 'error'}

        payment_period_start, payment_period_end, payment_periodicity_code = self._get_period_bounds(
            company_id, period_start, "payment",
        )
        payment_source_moves = self._get_payment_source_moves(company_id, payment_period_start, payment_period_end)
        payment_moves = self._get_payment_moves(payment_source_moves)
        base_domain = [
            ("company_id", "=", company_id),
            ("currency_id", "=", currency_id),
            ("flow_type", "=", 'transaction_report'),
        ]
        payment_domain = base_domain + [
            ("report_kind", "=", "payment"),
            ("period_start", "=", payment_period_start),
            ("period_end", "=", payment_period_end),
            ("periodicity_code", "=", payment_periodicity_code),
        ]
        payment_flows = flow_model.search(payment_domain + [("is_correction", "=", False)], order="create_date asc")

        if not payment_moves and not payment_flows:
            return flow_model.browse(), flow_model.browse()

        payment_open_flows = payment_flows.filtered(lambda f: f.state in open_states)
        payment_closed_flows = payment_flows - payment_open_flows
        payment_flow = payment_open_flows[:1]
        rebuild_flows = flow_model.browse()
        last_sent_payment = payment_closed_flows.sorted("create_date")[-1:] if payment_closed_flows else flow_model.browse()

        if not payment_flow and last_sent_payment and payment_moves == last_sent_payment.move_ids:
            return last_sent_payment, rebuild_flows

        is_new_payment_flow = False
        payment_changed = False

        if payment_flow:
            # Existing flow - synchronize moves
            payment_changed = payment_flow._synchronize_moves(payment_moves)
            payment_open_flows = payment_open_flows - payment_flow
        else:
            # New flow - determine transmission type
            if last_sent_payment and last_sent_payment.move_ids and last_sent_payment.move_ids & payment_moves:
                payment_transmission = "MO"
                payment_reference = last_sent_payment.transport_identifier or False
                payment_reference_type = last_sent_payment.transmission_type or "IN"
                payment_is_correction = True
            else:
                payment_transmission = "CO" if payment_flows else "IN"
                payment_reference = False
                payment_reference_type = False
                payment_is_correction = False

            payment_flow = flow_model.create({
                "company_id": company_id,
                "reporting_date": payment_period_start,
                "currency_id": currency_id,
                "document_type": "sale",
                "flow_type": 'transaction_report',
                "transaction_type": transaction_type,
                "report_kind": "payment",
                "transmission_type": payment_transmission,
                "is_correction": payment_is_correction,
                "transmission_reference": payment_reference,
                "transmission_reference_type": payment_reference_type,
                "period_start": payment_period_start,
                "period_end": payment_period_end,
                "periodicity_code": payment_periodicity_code,
                "issue_datetime": fields.Datetime.now(),
                "move_ids": [Command.set(payment_moves.ids)],
            })
            payment_flow._reset_slices(payment_moves)
            payment_flow._update_reference_name()
            payment_flow._ensure_tracking_id()
            payment_changed = True
            is_new_payment_flow = True

        # Update existing payment flows only (not newly created ones)
        if payment_flow and not is_new_payment_flow:
            payment_flow.write({
                "reporting_date": payment_period_start,
                "period_start": payment_period_start,
                "period_end": payment_period_end,
                "periodicity_code": payment_periodicity_code,
                "report_kind": "payment",
                "document_type": "sale",
                "issue_datetime": fields.Datetime.now(),
            })
            payment_flow._update_reference_name()
            payment_flow._ensure_tracking_id()

        if payment_flow:
            if payment_flow.state not in open_states:
                payment_flow.state = "draft"
            if payment_flow.transaction_type != transaction_type:
                payment_flow.transaction_type = transaction_type
            if payment_changed or not payment_flow.has_payload:
                rebuild_flows |= payment_flow

        # Clean up unused payment flows
        if payment_open_flows:
            payment_open_flows._synchronize_moves(self.env["account.move"].browse())
            payment_open_flows.unlink()

        return payment_flow, rebuild_flows

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_payment_moves(self, moves):
        """Filter moves that have associated payments."""
        payment_moves = self.env["account.move"].browse()
        for move in moves:
            if move.move_type == "out_receipt" and move.amount_total:
                payment_moves |= move
                continue
            for partial in move._get_all_reconciled_invoice_partials():
                if aml := partial.get("aml"):
                    amount = partial.get("amount")
                    if amount is None:
                        amount = abs(aml.amount_currency) if aml.currency_id and aml.amount_currency else abs(aml.balance or 0.0)
                    if amount:
                        payment_moves |= move
                        break
        return payment_moves

    def _get_payment_source_moves(self, company_id, period_start, period_end):
        """Sale docs with payments dated in the payment window."""
        sale_types = self.env["account.move"].get_sale_types(include_receipts=True)
        candidates = self.env["account.move"].search([
            ("company_id", "=", company_id),
            ("state", "=", "posted"),
            ("move_type", "in", sale_types),
            ("payment_state", "!=", "not_paid"),
        ], order="invoice_date, id")
        result = self.env["account.move"].browse()
        for move in candidates:
            # Cash receipt acts as its own payment.
            pay_date = move.invoice_date or move.date
            if move.move_type == "out_receipt" and period_start <= pay_date <= period_end:
                result |= move
                continue
            # Find reconciled payment lines dated in the window.
            for partial in move._get_all_reconciled_invoice_partials():
                aml = partial.get("aml")
                if aml and period_start <= aml.date <= period_end:
                    result |= move
                    break
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
