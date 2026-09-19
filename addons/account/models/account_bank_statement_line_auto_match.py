import logging

from odoo import api, fields, models, modules, service
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, float_compare

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)

MAX_BARREN_CRON_ROUNDS = 3


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @_debug.perf.timed
    def _cron_try_auto_reconcile_statement_lines(
        self, batch_size=None, limit_time=0, company_id=None
    ):
        _debug.lifecycle("_cron_try_auto_reconcile_statement_lines", records=self)
        if limit_time <= 0:
            # `limit_time_real_cron` DEFAULTS to -1, meaning "inherit
            # --limit-time-real" (itself 120), and reading the option directly
            # cannot see that: -1 fell through to the 180 default, so the cron
            # budgeted itself 50% longer than the server's own request limit.
            # The service helper resolves the inheritance.
            cron_limit_time = service.get_cron_real_time_budget() or -1
            limit_time = cron_limit_time if 0 < cron_limit_time < 180 else 180

        _debug.logic(
            "cron_budget_resolved",
            limit_time=limit_time,
            batch_size=batch_size,
            company=company_id,
        )
        if limit_time and not batch_size:
            _logger.warning(
                "_cron_try_auto_reconcile_statement_lines called with "
                "limit_time=%r but batch_size=%r won't limit anything",
                limit_time,
                batch_size,
            )

        def compute_st_lines_to_reconcile(company_id=None):
            remaining_line_id = None
            limit = batch_size + 1 if batch_size else None
            domain = Domain(
                [
                    ("is_reconciled", "=", False),
                    ("cron_last_check", "=", False),
                ]
            )
            if company_id is not None:
                domain &= Domain(
                    self.env["account.reconcile.model"]._check_company_domain(
                        company_id
                    )
                )
            st_lines = self.search(domain, limit=limit, order="id")
            _logger.info(
                "_cron_try_auto_reconcile_statement_lines found %s statement lines",
                len(st_lines),
            )
            if batch_size and len(st_lines) > batch_size:
                remaining_line_id = st_lines[batch_size].id
                st_lines = st_lines[:batch_size]
            _debug.pipeline(
                "cron_batch_selected",
                automatch=st_lines,
                count=len(st_lines),
                remaining_line_id=remaining_line_id,
            )
            return st_lines, remaining_line_id

        def is_limit_time_exceeded():
            if batch_size and limit_time:
                return (
                    fields.Datetime.now().timestamp() - start_time.timestamp()
                    > limit_time
                )
            return False

        can_commit = not modules.module.current_test and not self.env.context.get(
            "import_file", False
        )
        remaining_line_id = None

        start_time = fields.Datetime.now()

        def rollback_and_retire(st_lines, exc):
            _logger.warning("Error while processing statement lines: %s", exc)
            retired = 0
            if not isinstance(exc, UserError) and can_commit:
                _logger.warning(
                    "_cron_try_auto_reconcile_statement_lines will rollback the cursor"
                )
                self.env.cr.rollback()
            for st_line in st_lines.exists():
                try:
                    with self.env.cr.savepoint():
                        st_line._try_auto_reconcile_statement_lines(
                            company_id=company_id
                        )
                except Exception as line_exc:
                    _logger.warning(
                        "_cron_try_auto_reconcile_statement_lines giving up on statement line %s: %s",
                        st_line.id,
                        line_exc,
                    )
                    st_line.cron_last_check = self.env.cr.now()
                    retired += 1
            _debug.pipeline(
                "cron_batch_retried_per_line",
                automatch=st_lines,
                error=type(exc).__name__,
                rolled_back=not isinstance(exc, UserError) and can_commit,
                retired=retired,
            )
            return retired

        barren_rounds = 0

        while not is_limit_time_exceeded():
            st_lines = self.browse()
            try:
                st_lines, remaining_line_id = compute_st_lines_to_reconcile(
                    company_id=company_id
                )

                if not st_lines:
                    return

                with _debug.perf(
                    "automatch_cron_batch", cr=self.env.cr, st_lines_count=len(st_lines)
                ):
                    st_lines._try_auto_reconcile_statement_lines(company_id=company_id)
                barren_rounds = 0
            except Exception as e:
                if rollback_and_retire(st_lines, e):
                    barren_rounds = 0
                else:
                    barren_rounds += 1
                    if barren_rounds >= MAX_BARREN_CRON_ROUNDS:
                        _logger.error(
                            "_cron_try_auto_reconcile_statement_lines gave up after %s "
                            "rounds that retired no statement line; last error: %s",
                            barren_rounds,
                            e,
                        )
                        return

            if can_commit:
                self.env.cr.commit()

        _debug.logic(
            "cron_time_budget_exhausted",
            remaining_line_id=remaining_line_id,
            barren_rounds=barren_rounds,
            rescheduled=bool(remaining_line_id),
        )
        if remaining_line_id:
            _logger.info(
                "_cron_try_auto_reconcile_statement_lines remaining line found (%s), the cron will be triggered again",
                remaining_line_id,
            )
            self.env.ref("account.auto_reconcile_bank_statement_line")._trigger()

    @api.model
    def _get_unmatched_amounts(self):
        # what the statement line still has to match, in the company
        # currency and in the line's currency, after the earlier steps
        self.check_singleton()
        _liquidity_lines, suspense_lines, _other_lines = self._seek_for_lines()
        if not self.checked:
            return self.amount, self.amount_currency or self.amount
        if suspense_lines.account_id.reconcile:
            return (
                -sum(suspense_lines.mapped("amount_residual")),
                -sum(suspense_lines.mapped("amount_residual_currency")),
            )
        return (
            -sum(suspense_lines.mapped("balance")),
            -sum(suspense_lines.mapped("amount_currency")),
        )

    def _settles_residual(
        self, amount, residual, discounted, discount_date, date, tolerance
    ):
        if residual == amount:
            return True
        if discount_date and discounted == amount and date <= discount_date:
            return True
        return abs(amount - residual) <= tolerance * abs(residual)

    @_debug.perf.timed
    def _invoice_matching_post_process(self, st_line, amls):
        candidate_amls = self.env["account.move.line"]
        tolerance = self._get_payment_tolerance()
        unmatched, unmatched_currency = st_line._get_unmatched_amounts()
        for aml in amls:
            readings = (
                (
                    aml.company_currency_id == st_line.currency_id,
                    aml.amount_residual,
                    aml.discount_balance,
                    unmatched,
                ),
                (
                    aml.currency_id == st_line.currency_id,
                    aml.amount_residual_currency,
                    aml.discount_amount_currency,
                    unmatched,
                ),
                (
                    aml.currency_id == st_line.foreign_currency_id,
                    aml.amount_residual_currency,
                    aml.discount_amount_currency,
                    unmatched_currency,
                ),
            )
            if any(
                applies
                and self._settles_residual(
                    amount,
                    residual,
                    discounted,
                    aml.discount_date,
                    st_line.date,
                    tolerance,
                )
                for applies, residual, discounted, amount in readings
            ):
                candidate_amls += aml

        prior_amls = candidate_amls.filtered(
            lambda aml: aml.invoice_date and aml.invoice_date <= st_line.date
        )
        _debug.logic(
            "invoice_matching_within_before",
            automatch=st_line,
            candidate_amls_count=len(candidate_amls),
            amls_count=len(amls),
            tolerance=tolerance,
            prior_amls_count=len(prior_amls),
        )
        if len(candidate_amls) == 1:
            return candidate_amls
        if len(prior_amls) == 1:
            return prior_amls
        return None

    @_debug.perf.timed
    def _handle_reconciliation_matching_amount(
        self, st_move_ids, account_ids, remaining_st_line_ids, match_journal=False
    ):
        processed_st_line_ids = set()
        journal_clause = (
            SQL("AND aml.journal_id = st_line.journal_id") if match_journal else SQL("")
        )
        query = SQL(
            """
                SELECT st_line.id AS st_line_id,
                       ARRAY_AGG(aml.id ORDER BY aml.id ASC) AS all_aml_ids,
                       SUM(aml.amount_residual) AS total_residual
                  FROM account_bank_statement_line st_line
                  JOIN account_move_line aml
                    ON st_line.partner_id = aml.partner_id
                   AND aml.company_id = st_line.company_id
                   AND SIGN(st_line.amount) = SIGN(aml.balance)
                       %s
                  JOIN account_move move ON aml.move_id = move.id
                 WHERE st_line.partner_id IS NOT NULL
                   AND aml.move_id != ALL(%s)
                   AND aml.reconciled = false
                   AND aml.account_id = ANY(%s)
                   AND (aml.parent_state IN ('draft', 'posted'))
                   AND st_line.id = ANY(%s)
              GROUP BY st_line.id
        """,
            journal_clause,
            list(st_move_ids),
            list(account_ids),
            list(remaining_st_line_ids),
        )
        self.env.cr.execute(query)
        _debug.perf.count("matching_amount_rows_fetched", rows=self.env.cr.rowcount)

        for st_line_id, all_aml_ids, total_residual in self.env.cr.fetchall():
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)
            unmatched, _unmatched_currency = st_line._get_unmatched_amounts()
            exact = (
                float_compare(
                    total_residual,
                    unmatched,
                    precision_rounding=st_line.currency_id.rounding,
                )
                == 0
            )
            _debug.logic(
                "matching",
                automatch=st_line_id,
                journal=match_journal,
                count=len(all_aml_ids or ()),
                residual=total_residual,
                amount=unmatched,
                exact=exact,
            )
            if exact:
                st_line.set_line_bank_statement_line(all_aml_ids)
                _logger.info(
                    "try_auto_reconcile - match amount - st_line: %s set lines %s",
                    st_line.id,
                    all_aml_ids,
                )
            elif all_aml_ids:
                amls = self.env["account.move.line"].browse(all_aml_ids)
                candidate_amls = self._invoice_matching_post_process(st_line, amls)
                if candidate_amls:
                    st_line.set_line_bank_statement_line(candidate_amls.ids)
                    _logger.info(
                        "try_auto_reconcile - _invoice_matching_post_process - st_line: %s set lines %s",
                        st_line.id,
                        candidate_amls.ids,
                    )
            if st_line.currency_id.is_zero(st_line.amount_residual):
                processed_st_line_ids.add(st_line.id)
        return processed_st_line_ids

    @_debug.perf.timed
    def _flush_before_matching_queries(self):
        self.env["account.account"].flush_model(["account_type", "active"])
        self.env["account.move"].flush_model(["date", "amount_total"])
        self.env["account.move.line"].flush_model(
            [
                "ref",
                "move_id",
                "move_name",
                "account_id",
                "partner_id",
                "company_id",
                "reconciled",
                "company_currency_id",
                "amount_residual",
                "currency_id",
                "amount_residual_currency",
                "discount_date",
                "discount_balance",
                "discount_amount_currency",
            ]
        )
        self.flush_recordset(
            [
                "move_id",
                "partner_id",
                "company_id",
                "currency_id",
                "amount",
                "foreign_currency_id",
                "amount_currency",
                "payment_ref",
            ]
        )
        self.env["account.payment"].flush_model(["move_id", "journal_id", "memo"])

    @_debug.perf.timed
    def _try_auto_reconcile_statement_lines(self, company_id=None):
        st_move_ids = self.mapped("move_id").ids
        self.lock_for_update()

        try:
            domain = []
            if company_id is not None:
                domain = Domain(
                    self.env["account.reconcile.model"]._check_company_domain(
                        company_id
                    )
                )
            reco_models = self.env["account.reconcile.model"].search(domain)

            self._partner_mapping(reco_models)
            self._flush_before_matching_queries()

            account_ids = self._get_matchable_account_ids()
            _debug.pipeline(
                "start_model_account",
                automatch=self,
                reco_models_count=len(reco_models),
                account_ids_count=len(account_ids),
            )

            remaining_st_line_ids = set(self.ids) - self._end_to_end_uuid(
                st_move_ids, account_ids
            )
            _debug.pipeline(
                "after_end_end_uuid",
                automatch=self,
                remaining_st_line_ids_count=len(remaining_st_line_ids),
            )
            if not remaining_st_line_ids:
                return

            outstanding_accounts = self._get_outstanding_payment_accounts()
            if outstanding_accounts:
                remaining_st_line_ids = self._match_outstanding_accounts(
                    st_move_ids, outstanding_accounts, remaining_st_line_ids
                )
                _debug.pipeline(
                    "after_outstanding_accounts",
                    automatch=self,
                    outstanding_accounts=outstanding_accounts,
                    remaining_st_line_ids_count=len(remaining_st_line_ids),
                )

            account_ids = list(set(account_ids) - set(outstanding_accounts.ids))
            if not (remaining_st_line_ids and account_ids):
                return

            remaining_st_line_ids = self._match_payment_references(
                st_move_ids, account_ids, remaining_st_line_ids
            )
            _debug.pipeline(
                "after_payment_references",
                automatch=self,
                remaining_st_line_ids_count=len(remaining_st_line_ids),
            )
            if not remaining_st_line_ids:
                return

            remaining_st_line_ids -= self._handle_reconciliation_matching_amount(
                st_move_ids, account_ids, remaining_st_line_ids
            )
            _debug.pipeline(
                "after_amount_matching",
                automatch=self,
                remaining_st_line_ids_count=len(remaining_st_line_ids),
            )
            if not remaining_st_line_ids:
                return

            remaining_st_lines = self.browse(list(remaining_st_line_ids)).with_prefetch(
                self._prefetch_ids
            )
            reco_models._apply_reconcile_models(remaining_st_lines)
            _logger.info(
                "try_auto_reconcile - apply reco models - st_lines: %s - reco models %s",
                remaining_st_lines.ids,
                reco_models.ids,
            )
        finally:
            self.write({"cron_last_check": self.env.cr.now()})
