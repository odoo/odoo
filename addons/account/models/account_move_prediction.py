import logging
import re

import psycopg

from odoo import api, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_predict_postgres_dictionary(self):
        lang = self.env.context.get("lang") and self.env.context.get("lang")[:2]
        return {"fr": "french"}.get(lang, "english")

    @api.model
    @_debug.perf.timed
    def _prepare_predictive_query(self, move_id, additional_domain=None, partner=None):
        move_query = self.env["account.move"]._search(
            [
                ("move_type", "=", move_id.move_type),
                ("state", "=", "posted"),
                ("partner_id", "=", (partner or move_id.partner_id).id),
                (
                    "company_id",
                    "=",
                    move_id.journal_id.company_id.id or self.env.company.id,
                ),
            ],
            bypass_access=True,
        )
        move_query.order = SQL("account_move.invoice_date")
        move_query.limit = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "account.bill.predict.history.limit",
                "100",
            )
        )
        _debug.pipeline(
            "predictive_history_scoped",
            move=move_id,
            partner=partner,
            history_limit=move_query.limit,
            extra_terms=len(additional_domain or []),
        )
        return self.env["account.move.line"]._search(
            [
                ("move_id", "in", move_query),
                ("display_type", "=", "product"),
            ]
            + (additional_domain or []),
            bypass_access=True,
        )

    @api.model
    @_debug.perf.timed
    def _predicted_field(
        self, move_id, name, partner_id, field, query=None, additional_queries=None
    ):
        if not name or not partner_id:
            return False

        psql_lang = self._get_predict_postgres_dictionary()
        description = name + " account_move_line"
        parsed_description = re.sub(r"[*&()|!':<>=%/~@,.;$\[\]]+", " ", description)
        parsed_description = " | ".join(parsed_description.split())

        try:
            main_source = (
                query
                if query is not None
                else self._prepare_predictive_query(move_id, partner=partner_id)
            ).select(
                SQL("%s AS prediction", field),
                SQL(
                    "setweight(to_tsvector(%s, account_move_line.name), 'B') || setweight(to_tsvector('simple', 'account_move_line'), 'A') AS document",
                    psql_lang,
                ),
            )
            if "(" in field.code:
                main_source = SQL(
                    "%s %s",
                    main_source,
                    SQL(
                        "GROUP BY account_move_line.id, account_move_line.name, account_move_line.partner_id"
                    ),
                )

            with self.env.cr.savepoint():
                self.env.cr.execute(
                    SQL(
                        """
                WITH account_move_line AS MATERIALIZED (%(account_move_line)s),

                source AS (%(source)s),

                ranking AS (
                    SELECT prediction, ts_rank(source.document, query_plain) AS rank
                      FROM source, to_tsquery(%(lang)s, %(description)s) query_plain
                     WHERE source.document @@ query_plain
                )

                SELECT prediction, MAX(rank) AS ranking, COUNT(*)
                  FROM ranking
              GROUP BY prediction
              ORDER BY ranking DESC, count DESC
                 LIMIT 2
                """,
                        account_move_line=self._prepare_predictive_query(
                            move_id, partner=partner_id
                        ).select(SQL("*")),
                        source=SQL(
                            "(%s)",
                            SQL(") UNION ALL (").join(
                                [main_source] + (additional_queries or [])
                            ),
                        ),
                        lang=psql_lang,
                        description=parsed_description,
                    )
                )
                result = self.env.cr.dictfetchall()
            _debug.logic(
                "predict_partner",
                code=field.code,
                partner_id=partner_id,
                parsed_description=parsed_description[:60],
                result=result,
            )
            if result:
                if (
                    len(result) > 1
                    and result[0]["ranking"] < 1.1 * result[1]["ranking"]
                ):
                    _debug.logic("predict_ambiguous_ranking_no_prediction")
                    return False
                return result[0]["prediction"]
        except psycopg.Error:
            _logger.exception("Error while predicting invoice line fields")
        return False

    def _predict_taxes(self):
        field = SQL(
            "array_agg(account_move_line__tax_rel__tax_ids.id ORDER BY account_move_line__tax_rel__tax_ids.id)"
        )
        query = self._prepare_predictive_query(self.move_id)
        query.left_join(
            "account_move_line",
            "id",
            "account_move_line_account_tax_rel",
            "account_move_line_id",
            "tax_rel",
        )
        query.left_join(
            "account_move_line__tax_rel",
            "account_tax_id",
            "account_tax",
            "id",
            "tax_ids",
        )
        query.add_where(SQL("account_move_line__tax_rel__tax_ids.active IS NOT FALSE"))
        predicted_tax_ids = self._predicted_field(
            self.move_id, self.name, self.partner_id, field, query
        )
        _debug.logic("taxes_predicted", line=self, tax_ids=predicted_tax_ids)
        if predicted_tax_ids == [None]:
            return False
        if predicted_tax_ids is not False and set(predicted_tax_ids) != set(
            self.tax_ids.ids
        ):
            return predicted_tax_ids
        return False

    @api.model
    @_debug.perf.timed
    def _predict_specific_tax(
        self, move, name, partner, amount_type, amount, type_tax_use
    ):
        field = SQL(
            "array_agg(account_move_line__tax_rel__tax_ids.id ORDER BY account_move_line__tax_rel__tax_ids.id)"
        )
        query = self._prepare_predictive_query(move, partner=partner)
        query.left_join(
            "account_move_line",
            "id",
            "account_move_line_account_tax_rel",
            "account_move_line_id",
            "tax_rel",
        )
        query.left_join(
            "account_move_line__tax_rel",
            "account_tax_id",
            "account_tax",
            "id",
            "tax_ids",
        )
        query.add_where(
            SQL(
                """
                account_move_line__tax_rel__tax_ids.active IS NOT FALSE
                AND account_move_line__tax_rel__tax_ids.amount_type = %s
                AND account_move_line__tax_rel__tax_ids.type_tax_use = %s
                AND account_move_line__tax_rel__tax_ids.amount = %s
                """,
                amount_type,
                type_tax_use,
                amount,
            ),
        )
        _debug.pipeline(
            "tax_prediction_query",
            move=move,
            partner=partner,
            amount_type=amount_type,
            type_tax_use=type_tax_use,
            amount=amount,
        )
        return self._predicted_field(move, name, partner, field, query)

    @api.model
    def _predict_specific_product(self, move, name, partner):
        predict_product = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("account_predictive_bills.predict_product", "1")
        )
        if predict_product and move.company_id.account_config_id.predict_bill_product:
            query = self._prepare_predictive_query(
                move_id=move,
                additional_domain=[
                    "|",
                    ("product_id", "=", False),
                    ("product_id.active", "=", True),
                ],
                partner=partner or move.partner_id,
            )
            return self._predicted_field(
                move, name, partner, SQL("account_move_line.product_id"), query
            )
        return False

    def _predict_product(self):
        predicted_product_id = self._predict_specific_product(
            self.move_id, self.name, self.partner_id
        )
        if predicted_product_id and predicted_product_id != self.product_id.id:
            return predicted_product_id
        return False

    @api.model
    @_debug.perf.timed
    def _predict_specific_account(self, move, name, partner):
        field = SQL("account_move_line.account_id")
        if move.is_purchase_document(True):
            excluded_group = "income"
        else:
            excluded_group = "expense"
        _debug.logic(
            "prediction_account_group_excluded", move=move, excluded=excluded_group
        )
        account_query = self.env["account.account"]._search(
            [
                *self.env["account.account"]._check_company_domain(
                    move.company_id or self.env.company
                ),
                ("internal_group", "not in", (excluded_group, "off")),
                ("account_type", "not in", ("liability_payable", "asset_receivable")),
            ],
            bypass_access=True,
        )
        account_name = self.env["account.account"]._field_to_sql(
            "account_account", "name"
        )
        psql_lang = self._get_predict_postgres_dictionary()
        additional_queries = [
            SQL(
                account_query.select(
                    SQL("account_account.id AS account_id"),
                    SQL(
                        "setweight(to_tsvector(%(psql_lang)s, %(account_name)s), 'B') AS document",
                        psql_lang=psql_lang,
                        account_name=account_name,
                    ),
                )
            )
        ]
        query = self._prepare_predictive_query(
            move, [("account_id", "in", account_query)], partner=partner
        )
        _debug.pipeline(
            "account_prediction_query",
            move=move,
            partner=partner,
            lang=psql_lang,
        )
        return self._predicted_field(
            move, name, partner, field, query, additional_queries
        )

    def _predict_account(self):
        predicted_account_id = self._predict_specific_account(
            self.move_id, self.name, self.partner_id
        )
        if predicted_account_id and predicted_account_id != self.account_id.id:
            return predicted_account_id
        return False

    def _predict_deductible_amount(self):
        if (
            self.account_id
            and self.partner_id
            and self.env.user.has_group("account.group_partial_purchase_deductibility")
        ):
            field = SQL("account_move_line.deductible_amount")
            query = self._prepare_predictive_query(
                self.move_id, [("account_id", "=", self.account_id.id)]
            )
            predicted_deductible_amount = self._predicted_field(
                self.move_id, self.name, self.partner_id, field, query
            )
            _debug.logic(
                "deductible_amount_predicted",
                line=self,
                amount=predicted_deductible_amount,
            )
            if (
                predicted_deductible_amount
                and predicted_deductible_amount != self.deductible_amount
            ):
                return predicted_deductible_amount
        return False

    @api.onchange("name")
    def _onchange_name_predictive(self):
        if (
            (self.move_id.quick_edit_mode or self.move_id.move_type == "in_invoice")
            and self.name
            and self.display_type == "product"
            and not self.env.context.get("disable_onchange_name_predictive", False)
        ):
            if not self.product_id:
                predicted_product_id = self._predict_product()
                _debug.logic(
                    "product_predicted", line=self, product_id=predicted_product_id
                )
                if predicted_product_id:
                    protected_fields = ["price_unit", "tax_ids", "name"]
                    to_protect = [
                        self._fields[fname] for fname in protected_fields if self[fname]
                    ]
                    with self.env.protecting(to_protect, self):
                        self.product_id = predicted_product_id

            if not self.product_id:
                predicted_account_id = self._predict_account()
                _debug.logic(
                    "account_predicted", line=self, account_id=predicted_account_id
                )
                if predicted_account_id:
                    self.account_id = predicted_account_id

                predicted_tax_ids = self._predict_taxes()
                if predicted_tax_ids:
                    self.tax_ids = [Command.set(predicted_tax_ids)]

            predicted_deductible_amount = self._predict_deductible_amount()
            if predicted_deductible_amount:
                self.deductible_amount = predicted_deductible_amount
