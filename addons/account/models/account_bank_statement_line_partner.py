from collections import defaultdict

from odoo import api, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.model
    def _first_unambiguous_partner(self, row, ranks):
        for bucket in ranks:
            candidates = row.get(bucket) or []
            if len(candidates) == 1:
                return candidates[0]
        return None

    def _partners_by_bank_account(self):
        lines = self.filtered("account_number")
        if not lines:
            return {}
        query = SQL(
            """
            SELECT ARRAY_AGG(DISTINCT partner_bank.partner_id) FILTER (WHERE partner_bank.company_id::TEXT = ANY(STRING_TO_ARRAY(company.parent_path, '/'))) AS account_matching_partner_with_company,
                   ARRAY_AGG(DISTINCT partner_bank.partner_id) FILTER (WHERE partner_bank.company_id IS NULL) AS account_matching_partner_without_company,
                   st_line.id AS st_line_id
              FROM res_partner_bank partner_bank
              JOIN account_bank_statement_line st_line ON partner_bank.sanitized_acc_number = NULLIF(REGEXP_REPLACE(st_line.account_number, '\\W+', '', 'g'), '')
              JOIN res_company company ON company.id = st_line.company_id
              JOIN res_partner partner ON partner.id = partner_bank.partner_id
             WHERE st_line.id = ANY(%(st_line_ids)s)
               AND partner.active
          GROUP BY st_line.id
        """,
            st_line_ids=lines.ids,
        )
        ranks = self._PARTNER_MATCH_RANKS["bank_account"]
        return {
            row["st_line_id"]: partner_id
            for row in self.env.execute_query_dict(query)
            if (partner_id := self._first_unambiguous_partner(row, ranks))
        }

    @_debug.perf.timed
    def _partners_by_transaction_name(self):
        lines = self.filtered("partner_name")
        _debug.pipeline(
            "partner_name_lookup_started",
            stline=self,
            with_partner_name=len(lines),
        )
        if not lines:
            return {}
        query = SQL(
            r"""
            SELECT ARRAY_AGG(partner.id) FILTER (WHERE partner.complete_name ILIKE st_line.name_pattern ESCAPE '\' AND partner.company_id::TEXT = ANY(STRING_TO_ARRAY(company.parent_path, '/'))) AS full_name_matching_partner_with_company,
                   ARRAY_AGG(partner.id) FILTER (WHERE partner.complete_name ILIKE st_line.name_pattern ESCAPE '\' AND partner.company_id IS NULL) AS full_name_matching_partner_without_company,
                   ARRAY_AGG(partner.id) FILTER (WHERE partner.complete_name ILIKE ('%%' || st_line.name_pattern || '%%') ESCAPE '\' AND partner.company_id::TEXT = ANY(STRING_TO_ARRAY(company.parent_path, '/'))) AS partial_name_matching_partner_with_company,
                   ARRAY_AGG(partner.id) FILTER (WHERE partner.complete_name ILIKE ('%%' || st_line.name_pattern || '%%') ESCAPE '\' AND partner.company_id IS NULL) AS partial_name_matching_partner_without_company,
                   st_line.id AS st_line_id
              FROM res_partner partner
              JOIN (
                        SELECT id,
                               company_id,
                               REPLACE(REPLACE(REPLACE(NULLIF(TRIM(partner_name), ''), '\', '\\'), '%%', '\%%'), '_', '\_') AS name_pattern
                          FROM account_bank_statement_line
                         WHERE id = ANY(%(st_line_ids)s)
                   ) st_line ON partner.complete_name ILIKE ('%%' || st_line.name_pattern || '%%') ESCAPE '\'
              JOIN res_company company ON company.id = st_line.company_id
             WHERE partner.parent_id IS NULL
               AND partner.id != ALL(%(blacklisted_partner_ids)s)
               AND partner.active
          GROUP BY st_line.id
        """,
            st_line_ids=lines.ids,
            blacklisted_partner_ids=self._get_blacklisted_partners().ids,
        )
        ranks = self._PARTNER_MATCH_RANKS["partner_name"]
        return {
            row["st_line_id"]: partner_id
            for row in self.env.execute_query_dict(query)
            if (partner_id := self._first_unambiguous_partner(row, ranks))
        }

    @_debug.perf.timed
    def _partners_by_earlier_transactions(self):
        lines = self.filtered("partner_name")
        _debug.pipeline(
            "earlier_transactions_lookup_started",
            stline=self,
            with_partner_name=len(lines),
        )
        if not lines:
            return {}
        query = SQL(
            """
            WITH st_lines AS (
                SELECT st_line.partner_id AS partner_id,
                       st_line.partner_name AS partner_name,
                       st_line.company_id AS company_id,
                       ROW_NUMBER() OVER (PARTITION BY st_line.partner_name ORDER BY st_line.id DESC) AS row_number
                  FROM account_bank_statement_line st_line
                  JOIN res_partner partner ON partner.id = st_line.partner_id
                 WHERE st_line.is_reconciled = TRUE
                   AND st_line.partner_name = ANY(%(partner_names)s)
                   AND st_line.company_id = ANY(%(company_ids)s)
                   AND partner.active
            )
            -- MIN() rather than a GROUP BY on the column: the HAVING already restricts
            -- each group to a single distinct partner, so any aggregate names it.
            SELECT MIN(partner_id) AS partner_id,
                   ARRAY_AGG(DISTINCT company_id) AS company_ids,
                   partner_name
              FROM st_lines
             WHERE st_lines.row_number <= 3
          GROUP BY partner_name
            HAVING COUNT(DISTINCT partner_id) = 1
        """,
            partner_names=lines.mapped("partner_name"),
            company_ids=lines.company_id.ids,
        )
        by_name = {
            row["partner_name"]: row for row in self.env.execute_query_dict(query)
        }
        _debug.pipeline(
            "earlier_transactions_names_resolved",
            stline=self,
            unambiguous_names=len(by_name),
        )
        return {
            line.id: match["partner_id"]
            for line in lines
            if (match := by_name.get(line.partner_name))
            and line.company_id.id in match["company_ids"]
        }

    def _set_partner_from_transaction(self):
        lines = self.filtered(lambda st_line: not st_line.partner_id)
        if not lines:
            return

        self.env.flush_all()

        for lookup in (
            "_partners_by_bank_account",
            "_partners_by_transaction_name",
            "_partners_by_earlier_transactions",
        ):
            decided = defaultdict(list)
            for st_line_id, partner_id in getattr(lines, lookup)().items():
                decided[partner_id].append(st_line_id)
            _debug.logic(
                "_set_partner_from_transaction",
                lookup=lookup,
                lines_count=len(lines),
                decided_count=len(decided),
            )
            for partner_id, st_line_ids in decided.items():
                self.browse(st_line_ids).partner_id = partner_id

            lines = lines.filtered(lambda st_line: not st_line.partner_id)
            if not lines:
                return

    def _get_blacklisted_partners(self):
        partners = self.env.ref("base.partner_root")
        if ai_agent := self.env.ref("ai.ai_default_agent", raise_if_not_found=False):
            partners += ai_agent.partner_id
        return partners

    def _get_partner_id(self, lines_to_add_partner_ids):
        self.check_singleton()
        if len(lines_to_add_partner_ids) == 1:
            return lines_to_add_partner_ids.pop()
        if len(lines_to_add_partner_ids) == 0:
            return self.partner_id.id
        return None

    def set_partner_bank_statement_line(self, partner_id):
        all_statement_lines = self
        if partner_names := [line.partner_name for line in self if line.partner_name]:
            all_statement_lines |= self.search(
                [
                    ("journal_id", "=", self.journal_id.id),
                    ("partner_name", "in", partner_names),
                    ("is_reconciled", "=", False),
                    ("partner_id", "=", False),
                ]
            )

        (all_statement_lines - self).move_id._track_set_author(
            self.env.ref("base.partner_root")
        )
        all_statement_lines.with_context(
            force_delete=True, skip_readonly_check=True
        ).partner_id = partner_id
        all_statement_lines._try_auto_reconcile_statement_lines()
