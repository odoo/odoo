import logging
import re
from collections import defaultdict

from odoo import SUPERUSER_ID, api, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_matchable_account_ids(self):
        companies = self.company_id
        accounts = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(companies),
                ("reconcile", "=", True),
                ("account_type", "not in", ("asset_cash", "liability_credit_card")),
            ]
        )
        accounts -= (
            self.env["account.journal"]
            .search(
                [
                    *self.env["account.journal"]._check_company_domain(companies),
                    ("type", "in", ["bank", "cash", "credit"]),
                ]
            )
            .suspense_account_id
        )
        return (accounts - self.journal_id.default_account_id).ids

    @api.model
    def _same_company_hierarchy_sql(self, left="left_company", right="right_company"):
        left, right = SQL.identifier(left), SQL.identifier(right)
        return SQL(
            "(%(left)s.parent_path LIKE %(right)s.parent_path || '%%'"
            " OR %(right)s.parent_path LIKE %(left)s.parent_path || '%%')",
            left=left,
            right=right,
        )

    @_debug.perf.timed
    def _match_outstanding_accounts(
        self, st_move_ids, outstanding_accounts, remaining_st_line_ids
    ):
        processed_st_line_ids = set()
        for (
            st_line_id,
            aml_id,
            _aml_amount_residual,
            _matching_word,
        ) in self._match_accounts_query(
            st_move_ids, outstanding_accounts.ids, remaining_st_line_ids, True
        ):
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)
            st_line.with_context(
                skip_account_review_check=True
            ).set_line_bank_statement_line(aml_id)
            _logger.info(
                "try_auto_reconcile - outstanding - st_line: %s set line %s",
                st_line.id,
                aml_id,
            )
            if st_line.currency_id.is_zero(st_line.amount_residual):
                processed_st_line_ids.add(st_line.id)

        remaining_st_line_ids -= processed_st_line_ids
        _debug.pipeline(
            "outstanding_references_matched",
            automatch=self,
            outstanding_accounts=outstanding_accounts,
            matched=len(processed_st_line_ids),
            remaining=len(remaining_st_line_ids),
            amount_fallback=bool(remaining_st_line_ids),
        )
        if remaining_st_line_ids:
            remaining_st_line_ids -= self._handle_reconciliation_matching_amount(
                st_move_ids,
                outstanding_accounts.ids,
                remaining_st_line_ids,
                match_journal=True,
            )
        return remaining_st_line_ids

    @_debug.perf.timed
    def _match_payment_references(
        self, st_move_ids, account_ids, remaining_st_line_ids
    ):
        processed_st_line_ids = set()
        matched_rows = self._match_accounts_query(
            st_move_ids, account_ids, remaining_st_line_ids
        )

        st_lines_refs = defaultdict(list)
        to_process = {}

        for (
            st_line_id,
            aml_id,
            aml_amount_residual,
            matching_word,
        ) in matched_rows:
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)
            if not self._is_properly_surrounded(st_line.payment_ref, matching_word):
                continue
            to_process[st_line_id, matching_word] = (aml_id, aml_amount_residual)
            for word in st_lines_refs[st_line_id]:
                if word in matching_word or matching_word in word:
                    to_process.pop((st_line_id, matching_word), None)
                    to_process.pop((st_line_id, word), None)
            st_lines_refs[st_line_id].append(matching_word)
        _debug.logic(
            "automatch_payment_references_after_surrounding",
            matched_rows_count=len(matched_rows),
            to_process_count=len(to_process),
        )

        ref_amls_left = {}
        for (st_line_id, _matching_word), (
            aml_id,
            aml_amount_residual,
        ) in to_process.items():
            st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)
            left = ref_amls_left.get(st_line_id)
            if left is None:
                ref_amls_left[st_line_id] = abs(st_line.amount) - abs(
                    aml_amount_residual
                )
            elif st_line.currency_id.compare_amounts(left, 0) <= 0:
                _debug.logic(
                    "payment_ref_amount_exhausted_aml",
                    automatch=st_line_id,
                    aml_id=aml_id,
                )
                continue
            else:
                ref_amls_left[st_line_id] = left - abs(aml_amount_residual)
            st_line.with_user(SUPERUSER_ID).set_line_bank_statement_line(aml_id)
            _logger.info(
                "try_auto_reconcile - payment ref - st_line: %s set line %s",
                st_line.id,
                aml_id,
            )
            if st_line.currency_id.is_zero(st_line.amount_residual):
                processed_st_line_ids.add(st_line.id)
        return remaining_st_line_ids - processed_st_line_ids

    def _get_outstanding_payment_accounts(self):
        return (
            self.env["account.payment.channel"]
            .search(
                self.env["account.payment.channel"]._check_company_domain(
                    self.company_id
                )
            )
            .payment_account_id
        ) - self.journal_id.default_account_id

    @_debug.perf.timed
    def _partner_mapping(self, reco_models):
        reco_model_model = self.env["account.reconcile.model"]
        reco_model_model.flush_model()
        self.env["account.move"].flush_model(["narration"])
        self.flush_recordset(
            [
                "journal_id",
                "amount",
                "transaction_details",
                "payment_ref",
                "partner_id",
                "company_id",
            ]
        )
        self.env.cr.execute(
            SQL(
                """
            WITH %(relations)s

          SELECT st_line.id AS st_line_id, reco_model.mapped_partner_id
            FROM account_bank_statement_line st_line
       LEFT JOIN LATERAL (
                   SELECT reco_model.id,
                          reco_model.mapped_partner_id
                     FROM account_reconcile_model reco_model
                          %(joins)s
                    WHERE %(match)s
                      AND reco_model.mapped_partner_id IS NOT NULL
                      AND reco_model.id = ANY(%(reco_models)s)
                 ORDER BY reco_model.created_automatically ASC NULLS FIRST, reco_model.sequence ASC, reco_model.id ASC
                    LIMIT 1
                 ) AS reco_model ON TRUE
           WHERE st_line.id = ANY(%(statement_lines)s)
             AND st_line.partner_id IS NULL
             AND reco_model.mapped_partner_id IS NOT NULL
            """,
                relations=reco_model_model._get_match_relations_cte(),
                joins=reco_model_model._get_match_joins_sql(),
                match=reco_model_model._get_match_sql(),
                reco_models=reco_models.ids,
                statement_lines=list(self.ids),
            )
        )

        mapped = defaultdict(list)
        for st_line_id, mapped_partner_id in self.env.cr.fetchall():
            mapped[mapped_partner_id].append(st_line_id)
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "partners_mapped_by_models",
                automatch=self,
                reco_models=len(reco_models),
                partners=len(mapped),
                st_lines=sum(len(ids) for ids in mapped.values()),
            )
        for mapped_partner_id, st_line_ids in mapped.items():
            self.browse(st_line_ids).partner_id = mapped_partner_id
            _logger.info(
                "try_auto_reconcile - partner mapping done for st_lines: %s and partner %s",
                st_line_ids,
                mapped_partner_id,
            )

    @_debug.perf.timed
    def _end_to_end_uuid(self, st_move_ids, account_ids):
        processed_st_line_ids = set()
        st_lines_with_end_to_end_uuid_ids = (
            "end_to_end_uuid" in self._fields and self.filtered("end_to_end_uuid").ids
        )
        if _debug.logic.enabled:
            _debug.logic(
                "end_to_end_uuid_candidates",
                automatch=self,
                field_present="end_to_end_uuid" in self._fields,
                candidates=len(st_lines_with_end_to_end_uuid_ids or ()),
            )
        if st_lines_with_end_to_end_uuid_ids:
            self.env.cr.execute(
                SQL(
                    """
                 -- Query to get either payment amls either invoice/bill amls related to payments which have
                 -- the same end to end uuid of bank statement lines.
                    SELECT st_line.id AS st_line_id,
                           ARRAY_AGG(aml.id ORDER BY aml.id ASC) AS aml_ids
                      FROM account_bank_statement_line st_line
                      JOIN account_payment payment ON st_line.end_to_end_uuid = payment.end_to_end_uuid
                      JOIN account_move_line aml ON (
                              payment.move_id = aml.move_id
                           OR aml.move_id IN (
                              SELECT move_payment_rel.invoice_id
                                FROM account_move__account_payment move_payment_rel
                               WHERE move_payment_rel.payment_id = payment.id
                           )
                      )
                 LEFT JOIN res_company aml_company ON aml_company.id = aml.company_id
                 LEFT JOIN res_company payment_company ON payment_company.id = payment.company_id
                 LEFT JOIN res_company st_line_company ON st_line_company.id = st_line.company_id
                     WHERE aml.move_id != ALL(%(st_move_ids)s)
                       AND %(aml_and_payment_related)s
                       AND %(st_line_and_payment_related)s
                       AND aml.reconciled = false
                       AND aml.account_id = ANY(%(account_ids)s)
                       AND ((st_line.amount > 0 AND aml.balance > 0) OR (st_line.amount < 0 AND aml.balance < 0))
                       AND aml.parent_state in ('draft', 'posted')
                       AND st_line.id = ANY(%(st_line_ids)s)
                  GROUP BY st_line.id
            """,
                    st_move_ids=list(st_move_ids),
                    account_ids=list(account_ids),
                    st_line_ids=list(st_lines_with_end_to_end_uuid_ids),
                    aml_and_payment_related=self._same_company_hierarchy_sql(
                        "aml_company", "payment_company"
                    ),
                    st_line_and_payment_related=self._same_company_hierarchy_sql(
                        "st_line_company", "payment_company"
                    ),
                )
            )
            _debug.perf.count("end_to_end_amls_fetched", rows=self.env.cr.rowcount)

            for st_line_id, aml_ids in self.env.cr.fetchall():
                st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)
                st_line.with_company(st_line.company_id).with_user(
                    SUPERUSER_ID
                ).set_line_bank_statement_line(aml_ids)
                processed_st_line_ids.add(st_line_id)

            _debug.pipeline(
                "end_to_end_amls_matched",
                automatch=self,
                matched=len(processed_st_line_ids),
            )
            if (
                st_lines_with_end_to_end_uuid_ids := set(
                    st_lines_with_end_to_end_uuid_ids
                )
                - processed_st_line_ids
            ):
                self.env.cr.execute(
                    SQL(
                        """
                    SELECT st_line.id as st_line_id,
                           payment.id as payment_id
                      FROM account_bank_statement_line st_line
                      JOIN account_payment payment ON st_line.end_to_end_uuid = payment.end_to_end_uuid
                 LEFT JOIN res_company st_line_company ON st_line_company.id = st_line.company_id
                 LEFT JOIN res_company payment_company ON payment_company.id = payment.company_id
                     WHERE st_line.id = ANY(%(st_line_ids)s)
                       AND %(st_line_and_payment_related)s
                       AND (
                             (st_line.amount > 0 AND payment.payment_type = 'inbound')
                           OR (st_line.amount < 0 AND payment.payment_type = 'outbound')
                       )
                       AND payment.state = ANY(%(payment_state)s)
                """,
                        st_line_ids=list(st_lines_with_end_to_end_uuid_ids),
                        st_line_and_payment_related=self._same_company_hierarchy_sql(
                            "st_line_company", "payment_company"
                        ),
                        payment_state=[
                            "draft",
                            *self.env["account.payment"]._valid_payment_states(),
                        ],
                    )
                )
                _debug.perf.count(
                    "end_to_end_payments_fetched", rows=self.env.cr.rowcount
                )
                for st_line_id, payment_id in self.env.cr.fetchall():
                    st_line = self.browse(st_line_id).with_prefetch(self._prefetch_ids)
                    payment = (
                        self.env["account.payment"]
                        .browse(payment_id)
                        .with_user(SUPERUSER_ID)
                    )
                    amls_to_create = payment.with_company(
                        st_line.company_id
                    )._get_amls_for_payment_without_move(date=st_line.date)
                    st_line.with_company(st_line.company_id).with_user(
                        SUPERUSER_ID
                    )._reconcile_with_payments(payment, amls_to_create)
                    processed_st_line_ids.add(st_line_id)
            _debug.pipeline(
                "end_to_end_payments_matched",
                automatch=self,
                processed=len(processed_st_line_ids),
            )
        return processed_st_line_ids

    @_debug.perf.timed
    def _match_accounts_query(
        self, st_move_ids, account_ids, remaining_st_line_ids, outstanding_account=False
    ):
        if outstanding_account:
            extra_condition = SQL("aml.journal_id = st_line.journal_id")
        else:
            extra_condition = SQL(
                "aml.currency_id = COALESCE(st_line.foreign_currency_id, st_line.currency_id)"
            )

        query = SQL(
            """
                SELECT st_line.id,
                       ARRAY_AGG(DISTINCT word_aml.id) aml_ids,
                       SUM(word_aml.amount_residual),
                       word_aml.word matching_word
                  FROM account_bank_statement_line st_line
          JOIN LATERAL (
                        SELECT aml.id, word, aml.ref, aml.amount_residual
                          FROM account_move_line aml
                     LEFT JOIN res_company aml_company ON aml_company.id = aml.company_id
                     LEFT JOIN res_company st_line_company ON st_line_company.id = st_line.company_id
                     LEFT JOIN account_move move ON (move.id = aml.move_id AND move.payment_reference != move.name),
                       LATERAL regexp_split_to_table(
                                  COALESCE(aml.ref, '') || ' - ' ||
                                  COALESCE(aml.move_name, '') || ' - ' ||
                                  COALESCE(move.payment_reference, ''), ' - '
                               ) AS word
                         WHERE (st_line.partner_id IS NULL OR st_line.partner_id = aml.partner_id)
                           AND aml.move_id != ALL(%(st_move_ids)s)
                           AND aml.reconciled = false
                           AND aml.account_id = ANY(%(account_ids)s)
                           AND %(aml_and_st_line_related)s
                           AND ((st_line.amount > 0 AND aml.balance > 0) OR (st_line.amount < 0 AND aml.balance < 0))
                           AND (aml.parent_state IN ('draft', 'posted'))
                           AND st_line.id = ANY(%(st_line_ids)s)
                           AND (
                                length(word) > 5 AND st_line.payment_ref ILIKE '%%' || word || '%%'
                               )
                           AND %(extra_condition)s
                       ) word_aml ON TRUE
              GROUP BY st_line.id, matching_word
                HAVING COUNT(DISTINCT word_aml.id) = 1
        """,
            st_move_ids=list(st_move_ids),
            account_ids=list(account_ids),
            st_line_ids=list(remaining_st_line_ids),
            aml_and_st_line_related=self._same_company_hierarchy_sql(
                "aml_company", "st_line_company"
            ),
            extra_condition=extra_condition,
        )
        _debug.pipeline(
            "reference_match_query_built",
            automatch=self,
            outstanding=outstanding_account,
            st_lines=len(remaining_st_line_ids),
            accounts=len(account_ids),
        )
        self.env.cr.execute(query)
        _debug.perf.count("reference_match_rows_fetched", rows=self.env.cr.rowcount)
        return self.env.cr.fetchall()

    @api.model
    def _is_properly_surrounded(self, text, substring):
        sub_escaped = re.escape(substring)
        pattern = rf"(^|[\s\.;,?!]){sub_escaped}($|[\s\.;,?!])"
        return re.search(pattern, text) is not None
