import logging

from odoo import SUPERUSER_ID, api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)

BANK_FEE_MAX_SHARE = 0.03

MATCH_FIELDS = frozenset(
    {
        "active",
        "company_id",
        "line_ids",
        "match_amount",
        "match_amount_max",
        "match_amount_min",
        "match_journal_ids",
        "match_label",
        "match_label_param",
        "match_partner_ids",
        "sequence",
        "trigger",
    }
)


class AccountReconcileModel(models.Model):
    _inherit = "account.reconcile.model"

    created_automatically = fields.Boolean(
        default=False,
        copy=False,
    )
    is_bank_fee_model = fields.Boolean(
        default=False,
        copy=False,
    )

    @api.model
    def _get_match_text_sql(self, st_line="st_line"):
        st_line = SQL.identifier(st_line)
        return SQL(
            """(
                     SELECT %(st_line)s.payment_ref AS txt
                      UNION ALL
                     SELECT move.narration
                       FROM account_move move
                      WHERE move.id = %(st_line)s.move_id
                      UNION ALL
                     SELECT leaf #>> '{}'
                       FROM jsonb_path_query(
                                COALESCE(%(st_line)s.transaction_details, '{}'::jsonb),
                                '$.**?(@.type() == "string")'
                            ) AS leaf
                   )""",
            st_line=st_line,
        )

    @api.model
    def _get_match_label_sql(self, st_line="st_line", reco_model="reco_model"):
        text = self._get_match_text_sql(st_line)
        param = SQL("%s.match_label_param", SQL.identifier(reco_model))
        literal = SQL(
            "EXISTS (SELECT 1 FROM %(text)s AS src"
            " WHERE src.txt IS NOT NULL AND strpos(lower(src.txt), lower(%(param)s)) > 0)",
            text=text,
            param=param,
        )
        regex = SQL(
            "EXISTS (SELECT 1 FROM %(text)s AS src"
            " WHERE src.txt IS NOT NULL AND src.txt ~* %(param)s)",
            text=text,
            param=param,
        )
        return SQL(
            """CASE %(match_label)s
                   WHEN 'contains'     THEN %(literal)s
                   WHEN 'not_contains' THEN NOT %(literal)s
                   WHEN 'match_regex'  THEN %(regex)s
                   ELSE TRUE
               END""",
            match_label=SQL("%s.match_label", SQL.identifier(reco_model)),
            literal=literal,
            regex=regex,
        )

    @api.model
    def _get_match_amount_sql(self, st_line="st_line", reco_model="reco_model"):
        minimum = SQL("COALESCE(%s.match_amount_min, 0.0)", SQL.identifier(reco_model))
        maximum = SQL("COALESCE(%s.match_amount_max, 0.0)", SQL.identifier(reco_model))
        amount = SQL("%s.amount", SQL.identifier(st_line))
        return SQL(
            """CASE COALESCE(%(match_amount)s, '')
                   WHEN 'lower'   THEN %(amount)s <= %(max)s
                   WHEN 'greater' THEN %(amount)s >= %(min)s
                   WHEN 'between' THEN %(amount)s BETWEEN LEAST(%(min)s, %(max)s)
                                                      AND GREATEST(%(min)s, %(max)s)
                   ELSE TRUE
               END""",
            match_amount=SQL("%s.match_amount", SQL.identifier(reco_model)),
            amount=amount,
            min=minimum,
            max=maximum,
        )

    @api.model
    def _get_match_relations_cte(self):
        return SQL(
            """matching_journal_ids AS (
                    SELECT account_reconcile_model_id,
                           ARRAY_AGG(account_journal_id) AS ids
                      FROM account_journal_account_reconcile_model_rel
                  GROUP BY account_reconcile_model_id
                 ),
                 matching_partner_ids AS (
                    SELECT account_reconcile_model_id,
                           ARRAY_AGG(res_partner_id) AS ids
                      FROM account_reconcile_model_res_partner_rel
                  GROUP BY account_reconcile_model_id
                 )"""
        )

    @api.model
    def _get_match_sql(self, st_line="st_line", reco_model="reco_model"):
        st_line_id = SQL.identifier(st_line)
        reco_model_id = SQL.identifier(reco_model)
        return SQL(
            """(matching_journal_ids.ids IS NULL OR %(st_line)s.journal_id = ANY(matching_journal_ids.ids))
               AND (matching_partner_ids.ids IS NULL OR %(st_line)s.partner_id = ANY(matching_partner_ids.ids))
               AND %(amount)s
               AND %(label)s
               AND %(reco_model)s.company_id = %(st_line)s.company_id
               AND %(reco_model)s.active IS TRUE""",
            st_line=st_line_id,
            reco_model=reco_model_id,
            amount=self._get_match_amount_sql(st_line, reco_model),
            label=self._get_match_label_sql(st_line, reco_model),
        )

    @api.model
    def _get_match_joins_sql(self, reco_model="reco_model"):
        reco_model = SQL.identifier(reco_model)
        return SQL(
            """LEFT JOIN matching_journal_ids ON %(reco_model)s.id = matching_journal_ids.account_reconcile_model_id
               LEFT JOIN matching_partner_ids ON %(reco_model)s.id = matching_partner_ids.account_reconcile_model_id""",
            reco_model=reco_model,
        )

    def _log_match_outcome(
        self,
        origin,
        prof,
        candidates,
        matched_model_ids,
        statement_line_count,
        matched_line_count,
    ):
        silent = candidates.filtered(lambda model: model.id not in matched_model_ids)
        _logger.debug(
            "[%.1f ms] %s: %d model(s) over %d statement line(s), %d line(s) matched; "
            "%d model(s) matched nothing%s",
            prof.elapsed * 1000,
            origin,
            len(candidates),
            statement_line_count,
            matched_line_count,
            len(silent),
            f": {', '.join(silent.mapped('name'))}" if silent else "",
        )

    @_debug.perf.timed
    def _apply_lines_for_bank_widget(
        self, residual_amount_currency, residual_balance, partner, st_line
    ):
        self.check_singleton()
        currency = (
            st_line.foreign_currency_id
            or st_line.journal_id.currency_id
            or st_line.company_currency_id
        )
        vals_list = []
        for line in self.line_ids:
            vals = line._apply_in_bank_widget(
                residual_amount_currency=residual_amount_currency,
                residual_balance=residual_balance,
                partner=line.partner_id or partner,
                st_line=st_line,
            )
            amount_currency = vals["amount_currency"]
            balance = vals["balance"]

            if currency.is_zero(
                amount_currency
            ) and st_line.company_currency_id.is_zero(balance):
                continue

            vals_list.append(vals)
            residual_amount_currency -= amount_currency
            residual_balance -= balance

        return vals_list

    @api.model
    @_debug.perf.timed
    def get_available_reconcile_model_per_statement_line(self, statement_line_ids):
        prof = _OrmProfile(_logger)
        self.check_access("read")
        statement_lines = (
            self.env["account.bank.statement.line"].browse(statement_line_ids).exists()
        )
        statement_lines.check_access("read")
        self.env["account.reconcile.model"].flush_model()
        self.env["account.bank.statement.line"].flush_model()
        self.env["account.move"].flush_model(["narration"])
        self.env.cr.execute(
            SQL(
                """
            WITH %(relations)s

          SELECT st_line.id AS st_line_id,
                 array_agg(reco_model.id ORDER BY reco_model.sequence ASC, reco_model.id ASC) AS reco_model_ids,
                 array_agg(reco_model.name ORDER BY reco_model.sequence ASC, reco_model.id ASC) AS reco_model_names
            FROM account_bank_statement_line st_line
       LEFT JOIN LATERAL (
                   SELECT DISTINCT reco_model.id,
                          reco_model.sequence,
                          COALESCE(reco_model.name -> %(lang)s, reco_model.name -> 'en_US') as name
                     FROM account_reconcile_model reco_model
                          %(joins)s
                LEFT JOIN account_reconcile_model_line reco_model_line ON reco_model_line.model_id = reco_model.id
                    WHERE %(match)s
                      AND reco_model.trigger = 'manual'
                      AND reco_model_line.account_id IS NOT NULL
                 ) AS reco_model ON TRUE
           WHERE st_line.id = ANY(%(statement_lines)s)
             AND reco_model.id IS NOT NULL
           GROUP BY st_line.id
            """,
                relations=self._get_match_relations_cte(),
                joins=self._get_match_joins_sql(),
                match=self._get_match_sql(),
                lang=self.env.lang,
                statement_lines=statement_lines.ids,
            )
        )
        query_result = self.env.cr.fetchall()
        prof.stop()
        _debug.pipeline(
            "manual_models_matched",
            stline=statement_lines,
            matched=len(query_result),
        )
        if prof.debug:
            self._log_match_outcome(
                "get_available_reconcile_model_per_statement_line",
                prof,
                candidates=self.search([("trigger", "=", "manual")]),
                matched_model_ids={
                    model_id for _st, ids, _names in query_result for model_id in ids
                },
                statement_line_count=len(statement_line_ids),
                matched_line_count=len(query_result),
            )
        return {
            st_line_id: [
                {"id": model_id, "display_name": model_name}
                for (model_id, model_name) in zip(model_ids, model_names, strict=True)
            ]
            for st_line_id, model_ids, model_names in query_result
        }

    @_debug.perf.timed
    def _apply_reconcile_models(self, statement_lines):
        if not self or not statement_lines:
            return
        prof = _OrmProfile(_logger)
        self.env["account.reconcile.model"].flush_model()
        self.env["account.move"].flush_model(["narration"])
        statement_lines.flush_recordset(
            [
                "journal_id",
                "amount",
                "amount_residual",
                "transaction_details",
                "payment_ref",
                "partner_id",
                "company_id",
            ]
        )
        self.env.cr.execute(
            SQL(
                """
            WITH %(relations)s,
                 model_fees AS (
                    SELECT model_fees.id,
                           model_fees.trigger,
                           matching_journal_ids.ids AS journal_ids
                      FROM account_reconcile_model model_fees
                      JOIN account_reconcile_model_line model_lines ON model_lines.model_id = model_fees.id
                 LEFT JOIN matching_journal_ids ON model_fees.id = matching_journal_ids.account_reconcile_model_id
                     WHERE model_fees.is_bank_fee_model IS TRUE
                       AND model_fees.active IS TRUE
                       AND model_lines.account_id IS NOT NULL
                 )

          SELECT st_line.id AS st_line_id,
                 COALESCE(reco_model.id, model_fees.id) AS reco_model_id,
                 COALESCE(reco_model.trigger, model_fees.trigger) AS trigger
            FROM account_bank_statement_line st_line
       LEFT JOIN LATERAL (
                   SELECT reco_model.id,
                          reco_model.trigger
                     FROM account_reconcile_model reco_model
                          %(joins)s
                    WHERE %(match)s
                      AND reco_model.id = ANY(%(reco_models)s)
                      AND reco_model.can_be_proposed IS TRUE
                 ORDER BY reco_model.sequence ASC, reco_model.id ASC
                    LIMIT 1
                 ) AS reco_model ON TRUE
       LEFT JOIN LATERAL (
                   SELECT model_fees.id,
                          model_fees.trigger
                     FROM model_fees
                    WHERE st_line.journal_id = ANY(model_fees.journal_ids)
                   -- Propose it on an incoming transaction whose unmatched remainder is
                   -- small enough to read as a bank charge. Deliberately NOT the payment
                   -- tolerance: that one decides whether a document counts as settled,
                   -- this one only decides whether to offer a button.
                      AND SIGN(st_line.amount) > 0
                      AND SIGN(st_line.amount_residual) > 0
                      AND ABS(st_line.amount_residual)
                          < %(fee_share)s * st_line.amount / (1 + %(fee_share)s)
                 ) AS model_fees ON TRUE
           WHERE st_line.id = ANY(%(statement_lines)s)
        """,
                relations=self._get_match_relations_cte(),
                joins=self._get_match_joins_sql(),
                match=self._get_match_sql(),
                fee_share=BANK_FEE_MAX_SHARE,
                reco_models=list(self.ids),
                statement_lines=list(statement_lines.ids),
            )
        )

        query_result = self.env.cr.fetchall()
        _debug.perf.count("reco_model_candidates_fetched", rows=len(query_result))
        prof.stop()
        if prof.debug:
            self._log_match_outcome(
                "_apply_reconcile_models",
                prof,
                candidates=self,
                matched_model_ids={
                    row[1] for row in query_result if row[1] is not None
                },
                statement_line_count=len(statement_lines),
                matched_line_count=sum(1 for row in query_result if row[1] is not None),
            )

        processed_st_line_ids = set()
        for st_line_id, reco_model_id, reco_model_trigger in query_result:
            if st_line_id in processed_st_line_ids or reco_model_id is None:
                continue

            st_line = (
                self.env["account.bank.statement.line"]
                .browse(st_line_id)
                .with_prefetch(statement_lines.ids)
            )
            reco_model = (
                self.env["account.reconcile.model"]
                .browse(reco_model_id)
                .with_prefetch(self.ids)
            )

            _debug.logic(
                "reco_model",
                automatch=st_line_id,
                reco_model_id=reco_model_id,
                trigger=reco_model_trigger,
            )
            if reco_model_trigger == "manual":
                st_line._action_manual_reco_model(reco_model_id)
            else:
                reco_model.with_user(SUPERUSER_ID)._trigger_reconciliation_model(
                    st_line.with_user(SUPERUSER_ID)
                )
            processed_st_line_ids.add(st_line_id)

    @_debug.perf.timed
    def _trigger_reconciliation_model(self, statement_line):
        self.check_singleton()
        liquidity_line, suspense_line, other_lines = statement_line._seek_for_lines()

        amls_to_create = list(
            self._apply_lines_for_bank_widget(
                residual_amount_currency=sum(suspense_line.mapped("amount_currency")),
                residual_balance=sum(suspense_line.mapped("balance")),
                partner=statement_line.partner_id,
                st_line=statement_line,
            )
        )
        _debug.pipeline(
            "reco_model_lines",
            automatch=statement_line,
            reco_model=self,
            line_count=len(amls_to_create),
            taxed=any(aml.get("tax_ids") for aml in amls_to_create),
        )
        if any(aml.get("tax_ids") for aml in amls_to_create):
            original_base_lines, original_tax_lines = (
                statement_line._prepare_for_tax_lines_recomputation()
            )

        statement_line._set_move_line_to_statement_line_move(
            liquidity_line + other_lines, amls_to_create
        )

        if any(aml.get("tax_ids") for aml in amls_to_create):
            _new_liquidity_line, new_suspense_line, _new_other_lines = (
                statement_line._seek_for_lines()
            )
            new_lines = statement_line.line_ids - (
                liquidity_line + other_lines + new_suspense_line
            )
            statement_line._create_tax_lines(
                original_base_lines, original_tax_lines, new_lines
            )

        if self.next_activity_type_id:
            statement_line.move_id.activity_schedule(
                activity_type_id=self.next_activity_type_id.id,
                user_id=self.env.user.id,
            )

    def trigger_reconciliation_model(self, statement_line_id):
        self.check_singleton()

        statement_lines = (
            self.env["account.bank.statement.line"].browse(statement_line_id).exists()
        )
        for statement_line in statement_lines:
            self._trigger_reconciliation_model(statement_line)

    def _get_unreconciled_statement_lines(self):
        if not self:
            return self.env["account.bank.statement.line"]
        return self.env["account.bank.statement.line"].search(
            [
                *self.env["account.bank.statement.line"]._check_company_domain(
                    self.company_id
                ),
                ("is_reconciled", "=", False),
            ]
        )

    def _clear_statement_line_proposals(self, statement_lines):
        if not statement_lines:
            return
        move_lines = self.env["account.move.line"].search(
            [
                ("reconcile_model_id", "in", self.ids),
                ("move_id.statement_line_id", "in", statement_lines.ids),
            ]
        )
        move_lines.filtered(
            lambda line: line.account_id == line.move_id.journal_id.suspense_account_id
        ).reconcile_model_id = False

    def _refresh_statement_line_proposals(self):
        statement_lines = self._get_unreconciled_statement_lines()
        if not statement_lines:
            return
        _debug.pipeline(
            "_refresh_statement_line_proposals_over_line",
            models=self,
            statement_lines_count=len(statement_lines),
        )
        self._clear_statement_line_proposals(statement_lines)
        active_models = self.filtered("active")
        if active_models:
            active_models._apply_reconcile_models(statement_lines)

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        res = super().write(vals)
        if MATCH_FIELDS.intersection(vals):
            self._refresh_statement_line_proposals()
        return res

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        reco_models = super().create(vals_list)
        reco_models.filtered("active")._refresh_statement_line_proposals()
        return reco_models
