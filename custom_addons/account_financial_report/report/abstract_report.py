# Copyright 2020 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AgedPartnerBalanceReport(models.AbstractModel):
    _name = "report.account_financial_report.abstract_report"
    _description = "Abstract Report"
    COMMON_ML_FIELDS = [
        "account_id",
        "partner_id",
        "journal_id",
        "date",
        "ref",
        "id",
        "move_id",
        "name",
    ]

    @api.model
    def _get_move_lines_domain_not_reconciled(
        self, company_id, account_ids, partner_ids, only_posted_moves, date_from
    ):
        domain = [
            ("account_id", "in", account_ids),
            ("company_id", "=", company_id),
            ("reconciled", "=", False),
        ]
        if partner_ids:
            domain += [("partner_id", "in", partner_ids)]
        if only_posted_moves:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["posted", "draft"])]
        if date_from:
            domain += [("date", ">", date_from)]
        return domain

    @api.model
    def _get_new_move_lines_domain(
        self, new_ml_ids, account_ids, company_id, partner_ids, only_posted_moves
    ):
        domain = [
            ("account_id", "in", account_ids),
            ("company_id", "=", company_id),
            ("id", "in", new_ml_ids),
        ]
        if partner_ids:
            domain += [("partner_id", "in", partner_ids)]
        if only_posted_moves:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["posted", "draft"])]
        return domain

    def _recalculate_move_lines(
        self,
        move_lines,
        debit_ids,
        credit_ids,
        debit_amount,
        credit_amount,
        ml_ids,
        account_ids,
        company_id,
        partner_ids,
        only_posted_moves,
        debit_amount_currency,
        credit_amount_currency,
    ):
        debit_ids = set(debit_ids)
        credit_ids = set(credit_ids)
        in_credit_but_not_in_debit = credit_ids - debit_ids
        reconciled_ids = list(debit_ids) + list(in_credit_but_not_in_debit)
        reconciled_ids = set(reconciled_ids)
        ml_ids = set(ml_ids)
        new_ml_ids = reconciled_ids - ml_ids
        new_ml_ids = list(new_ml_ids)
        new_domain = self._get_new_move_lines_domain(
            new_ml_ids, account_ids, company_id, partner_ids, only_posted_moves
        )
        company_currency = self.env["res.company"].browse(company_id).currency_id
        ml_fields = self._get_ml_fields()
        new_move_lines = self.env["account.move.line"].search_read(
            domain=new_domain, fields=ml_fields
        )
        move_lines = move_lines + new_move_lines
        for move_line in move_lines:
            ml_id = move_line["id"]
            if ml_id in debit_ids:
                if move_line.get("amount_residual", False):
                    move_line["amount_residual"] += debit_amount[ml_id]
                else:
                    move_line["amount_residual"] = debit_amount[ml_id]
                if move_line.get("amount_residual_currency", False):
                    move_line["amount_residual_currency"] += debit_amount_currency[
                        ml_id
                    ]
                else:
                    move_line["amount_residual_currency"] = debit_amount_currency[ml_id]
            if ml_id in credit_ids:
                if move_line.get("amount_residual", False):
                    move_line["amount_residual"] -= credit_amount[ml_id]
                else:
                    move_line["amount_residual"] = -credit_amount[ml_id]
                if move_line.get("amount_residual_currency", False):
                    move_line["amount_residual_currency"] -= credit_amount_currency[
                        ml_id
                    ]
                else:
                    move_line["amount_residual_currency"] = -credit_amount_currency[
                        ml_id
                    ]
            # Set amount_currency=0 to keep the same behaviour as in v13
            # Conditions: if there is no curency_id defined or it is equal
            # to the company's curency_id
            if "amount_currency" in move_line and (
                "currency_id" not in move_line
                or move_line["currency_id"] == company_currency.id
            ):
                move_line["amount_currency"] = 0
        return move_lines

    def _get_accounts_data(self, accounts_ids):
        accounts = self.env["account.account"].browse(accounts_ids)
        accounts_data = {}
        for account in accounts:
            accounts_data.update(
                {
                    account.id: {
                        "id": account.id,
                        "code": account.code,
                        "name": account.name,
                        "hide_account": False,
                        "group_id": account.group_id.id,
                        "currency_id": account.currency_id.id,
                        "currency_name": account.currency_id.name,
                        "centralized": account.centralized,
                    }
                }
            )
        return accounts_data

    def _get_journals_data(self, journals_ids):
        journals = self.env["account.journal"].search_fetch(
            [("id", "in", journals_ids)], ["code"]
        )
        journals_data = {}
        for journal in journals:
            journals_data.update({journal.id: {"id": journal.id, "code": journal.code}})
        return journals_data

    def _get_ml_fields(self):
        return self.COMMON_ML_FIELDS + [
            "amount_residual",
            "reconciled",
            "currency_id",
            "credit",
            "date_maturity",
            "amount_residual_currency",
            "debit",
            "amount_currency",
        ]
