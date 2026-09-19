from datetime import date, timedelta

from odoo import api, fields, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, float_is_zero

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    @_debug.perf.timed
    def _get_frequent_account_and_taxes(self, company_id, partner_id, move_type):
        if _debug.logic.enabled and not partner_id:
            _debug.logic("frequent_account_skipped", reason="no_partner")
        if not partner_id:
            return 0, False, False
        domain = [
            *self.env["account.move.line"]._check_company_domain(company_id),
            ("partner_id", "=", partner_id),
            ("date", ">=", date.today() - timedelta(days=365 * 2)),
        ]
        if move_type in self.env["account.move"].get_inbound_types(
            include_receipts=True
        ):
            domain.append(("account_id.internal_group", "=", "income"))
        elif move_type in self.env["account.move"].get_outbound_types(
            include_receipts=True
        ):
            domain.append(("account_id.internal_group", "=", "expense"))

        query = self.env["account.move.line"]._search(domain)
        account_code = self.env["account.account"]._field_to_sql(
            "account_move_line__account_id", "code", query
        )
        rows = self.env.execute_query(
            SQL(
                """
            SELECT COUNT(foo.id), foo.account_id, foo.taxes
              FROM (
                         SELECT account_move_line__account_id.id AS account_id,
                                %(account_code)s AS code,
                                account_move_line.id,
                                ARRAY_AGG(tax_rel.account_tax_id) FILTER (WHERE tax_rel.account_tax_id IS NOT NULL) AS taxes
                           FROM %(from_clause)s
                      LEFT JOIN account_move_line_account_tax_rel tax_rel ON account_move_line.id = tax_rel.account_move_line_id
                          WHERE %(where_clause)s
                       GROUP BY account_move_line__account_id.id,
                                %(account_code)s,
                                account_move_line.id
                   ) AS foo
          GROUP BY foo.account_id, foo.taxes
          ORDER BY COUNT(foo.id) DESC, taxes ASC NULLS LAST
             LIMIT 1
            """,
                account_code=account_code,
                from_clause=query.from_clause,
                where_clause=query.where_clause or SQL("TRUE"),
            )
        )
        _debug.logic(
            "frequent_account_found",
            company=company_id,
            partner=partner_id,
            move_type=move_type,
            count=rows[0][0] if rows else 0,
            account=rows[0][1] if rows else False,
        )
        return rows[0] if rows else (0, False, False)

    @_debug.perf.timed
    def _get_quick_edit_suggestions(self):
        self.check_singleton()
        if _debug.logic.enabled and (
            not self.quick_edit_mode or not self.quick_edit_total_amount
        ):
            _debug.logic(
                "quick_edit_skipped",
                move=self,
                reason="mode_off" if not self.quick_edit_mode else "no_total",
            )
        if not self.quick_edit_mode or not self.quick_edit_total_amount:
            return False
        count, account_id, tax_ids = self._get_frequent_account_and_taxes(
            self.company_id.id,
            self.partner_id.id,
            self.move_type,
        )
        if count:
            taxes = self.fiscal_position_id.map_tax(
                self.env["account.tax"].browse(tax_ids)
            )
        else:
            account_id = self.journal_id.default_account_id.id
            if self.is_sale_document(include_receipts=True):
                taxes = self.journal_id.default_account_id.tax_ids.filtered(
                    lambda tax: tax.type_tax_use == "sale"
                )
            else:
                taxes = self.journal_id.default_account_id.tax_ids.filtered(
                    lambda tax: tax.type_tax_use == "purchase"
                )
            if not taxes:
                taxes = (
                    self.journal_id.company_id.account_config_id.account_sale_tax_id
                    if self.journal_id.type == "sale"
                    else self.journal_id.company_id.account_config_id.account_purchase_tax_id
                )
            taxes = self.fiscal_position_id.map_tax(taxes)

        _debug.logic(
            "quick_edit_account_source",
            move=self,
            from_history=bool(count),
            account=account_id,
            taxes=taxes,
        )
        term = self.invoice_payment_term_id
        discount_percentage = term.discount_percentage if term.early_discount else 0
        remaining_amount = (
            self.quick_edit_total_amount - self.tax_totals["total_amount_currency"]
        )

        if _debug.logic.enabled:
            _debug.logic(
                "quick_edit_price_mode",
                move=self,
                mixed_epd=bool(
                    discount_percentage
                    and term.early_pay_discount_computation == "mixed"
                    and len(taxes) == 1
                    and taxes.amount_type == "percent"
                ),
                remaining=remaining_amount,
            )
        if (
            discount_percentage
            and term.early_pay_discount_computation == "mixed"
            and len(taxes) == 1
            and taxes.amount_type == "percent"
        ):
            price_untaxed = self.currency_id.round(
                remaining_amount
                / (((1.0 - discount_percentage / 100.0) * (taxes.amount / 100.0)) + 1.0)
            )
        else:
            price_untaxed = taxes.with_context(force_price_include=True).compute_all(
                remaining_amount
            )["total_excluded"]
        return {
            "account_id": account_id,
            "tax_ids": taxes.ids,
            "price_unit": price_untaxed,
        }

    def _get_last_posted_dated_move(self, journal, company):
        return self.search(
            [
                ("state", "=", "posted"),
                ("journal_id", "=", journal.id),
                ("company_id", "=", company.id),
                ("invoice_date", "!=", False),
            ],
            limit=1,
        )

    @api.onchange("quick_edit_mode", "journal_id", "company_id")
    def _quick_edit_mode_suggest_invoice_date(self):
        for record in self:
            if record.quick_edit_mode and not record.invoice_date:
                invoice_date = fields.Date.context_today(self)
                prev_move = self._get_last_posted_dated_move(
                    record.journal_id, record.company_id
                )
                if prev_move:
                    invoice_date = self._get_accounting_date(
                        prev_move.invoice_date, False
                    )
                record.invoice_date = invoice_date

    @api.onchange("quick_edit_total_amount", "partner_id")
    def _onchange_quick_edit_total_amount(self):
        if (
            not self.quick_edit_total_amount
            or not self.quick_edit_mode
            or len(self.invoice_line_ids) > 0
        ):
            return
        suggestions = self.quick_encoding_vals
        self.invoice_line_ids = [Command.clear()]
        self.invoice_line_ids += self.env["account.move.line"].new(
            {
                "partner_id": self.partner_id,
                "account_id": suggestions["account_id"],
                "currency_id": self.currency_id.id,
                "price_unit": suggestions["price_unit"],
                "tax_ids": [Command.set(suggestions["tax_ids"])],
            }
        )
        self._check_total_amount(self.quick_edit_total_amount)

    @api.onchange("invoice_line_ids")
    def _onchange_quick_edit_line_ids(self):
        quick_encode_suggestion = self.env.context.get("quick_encoding_vals")
        if (
            not self.quick_edit_total_amount
            or not self.quick_edit_mode
            or not self.invoice_line_ids
            or not quick_encode_suggestion
            or quick_encode_suggestion["price_unit"]
            != self.invoice_line_ids[-1].price_unit
        ):
            return
        self._check_total_amount(self.quick_edit_total_amount)

    @_debug.perf.timed
    def _check_total_amount(self, amount_total):
        if not self.tax_totals or not amount_total:
            return
        totals = self.tax_totals
        tax_amount_rounding_error = amount_total - totals["total_amount_currency"]
        if not float_is_zero(
            tax_amount_rounding_error, precision_rounding=self.currency_id.rounding
        ):
            for subtotal in totals["subtotals"][:1]:
                if subtotal["tax_groups"]:
                    subtotal["tax_groups"][0]["tax_amount_currency"] += (
                        tax_amount_rounding_error
                    )
                    totals["total_amount_currency"] = amount_total
                    self.tax_totals = totals
