# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import itertools
import operator
from collections import defaultdict

from odoo import models


class JournalLedgerReport(models.AbstractModel):
    _name = "report.account_financial_report.journal_ledger"
    _description = "Journal Ledger Report"

    def _get_journal_ledger_data(self, journal):
        return {
            "id": journal.id,
            "name": journal.name,
            "currency_id": journal.currency_id.id,
            "currency_name": journal.currency_id
            and journal.currency_id.name
            or journal.company_id.currency_id.name,
            "debit": 0.0,
            "credit": 0.0,
        }

    def _get_journal_ledgers_domain(self, wizard, journal_ids, company):
        domain = []
        if company:
            domain += [("company_id", "=", company.id)]
        if journal_ids:
            domain += [("id", "in", journal_ids)]
        return domain

    def _get_journal_ledgers(self, wizard, journal_ids, company):
        journals = self.env["account.journal"].search(
            self._get_journal_ledgers_domain(wizard, journal_ids, company),
            order="name asc",
        )
        journal_ledgers_data = []
        for journal in journals:
            journal_ledgers_data.append(self._get_journal_ledger_data(journal))
        return journal_ledgers_data

    def _get_moves_domain(self, wizard, journal_ids):
        domain = [
            ("journal_id", "in", journal_ids),
            ("date", ">=", wizard.date_from),
            ("date", "<=", wizard.date_to),
        ]
        if wizard.move_target != "all":
            domain += [("state", "=", wizard.move_target)]
        else:
            domain += [("state", "in", ["posted", "draft"])]
        return domain

    def _get_moves_order(self, wizard, journal_ids):
        search_order = ""
        if wizard.sort_option == "move_name":
            search_order = "name asc"
        elif wizard.sort_option == "date":
            search_order = "date asc, name asc"
        return search_order

    def _get_moves_data(self, move):
        return {
            "move_id": move.id,
            "journal_id": move.journal_id.id,
            "entry": move.name,
        }

    def _get_moves(self, wizard, journal_ids):
        moves = self.env["account.move"].search(
            self._get_moves_domain(wizard, journal_ids),
            order=self._get_moves_order(wizard, journal_ids),
        )
        Moves = []
        move_data = {}
        for move in moves:
            move_data[move.id] = self._get_moves_data(move)
            Moves.append(move_data[move.id])
        return moves.ids, Moves, move_data

    def _get_move_lines_domain(self, move_ids, wizard, journal_ids):
        return [
            ("display_type", "not in", ["line_note", "line_section"]),
            ("move_id", "in", move_ids),
        ]

    def _get_move_lines_order(self, move_ids, wizard, journal_ids):
        """Add `move_id` to make sure the order of the records is correct
        (especially if we use auto-sequence).
        """
        return "move_id"

    def _get_move_lines_data(self, ml, wizard, ml_taxes, auto_sequence, exigible):
        base_debit = base_credit = tax_debit = tax_credit = base_balance = (
            tax_balance
        ) = 0.0
        if exigible:
            base_debit = ml_taxes and ml.debit or 0.0
            base_credit = ml_taxes and ml.credit or 0.0
            base_balance = ml_taxes and ml.balance or 0.0
            tax_debit = ml.tax_line_id and ml.debit or 0.0
            tax_credit = ml.tax_line_id and ml.credit or 0.0
            tax_balance = ml.tax_line_id and ml.balance or 0.0
        return {
            "move_line_id": ml.id,
            "move_id": ml.move_id.id,
            "date": ml.date,
            "journal_id": ml.journal_id.id,
            "account_id": ml.account_id.id,
            "partner_id": ml.partner_id.id,
            "label": ml.name,
            "debit": ml.debit,
            "credit": ml.credit,
            "company_currency_id": ml.company_currency_id.id,
            "amount_currency": ml.amount_currency,
            "currency_id": ml.currency_id.id,
            "tax_line_id": ml.tax_line_id.id,
            "tax_ids": list(ml_taxes.keys()),
            "base_debit": base_debit,
            "base_credit": base_credit,
            "tax_debit": tax_debit,
            "tax_credit": tax_credit,
            "base_balance": base_balance,
            "tax_balance": tax_balance,
            "auto_sequence": str(auto_sequence).zfill(6),
        }

    def _get_account_data(self, accounts):
        data = {}
        for account in accounts:
            data[account.id] = self._get_account_id_data(account)
        return data

    def _get_account_id_data(self, account):
        return {
            "name": account.name,
            "code": account.code,
            "account_type": account.account_type,
        }

    def _get_partner_data(self, partners):
        data = {}
        for partner in partners:
            data[partner.id] = self._get_partner_id_data(partner)
        return data

    def _get_partner_id_data(self, partner):
        return {"name": partner.name}

    def _get_currency_data(self, currencies):
        data = {}
        for currency in currencies:
            data[currency.id] = self._get_currency_id_data(currency)
        return data

    def _get_currency_id_data(self, currency):
        return {"name": currency.name}

    def _get_tax_line_data(self, taxes):
        data = {}
        for tax in taxes:
            data[tax.id] = self._get_tax_line_id_data(tax)
        return data

    def _get_tax_line_id_data(self, tax):
        return {"name": tax.name, "description": tax.description}

    def _get_query_taxes(self):
        return """
            SELECT aml_at_rel.account_move_line_id, aml_at_rel.account_tax_id,
            at.description, at.name
            FROM account_move_line_account_tax_rel AS aml_at_rel
            LEFT JOIN
                account_tax AS at on (at.id = aml_at_rel.account_tax_id)
            WHERE account_move_line_id IN %(move_line_ids)s
        """

    def _get_query_taxes_params(self, move_lines):
        return {"move_line_ids": tuple(move_lines.ids)}

    def _get_move_lines(self, move_ids, wizard, journal_ids):
        move_lines = (
            self.env["account.move.line"]
            .with_context(prefetch_fields=False)
            .search(
                self._get_move_lines_domain(move_ids, wizard, journal_ids),
                order=self._get_move_lines_order(move_ids, wizard, journal_ids),
            )
        )
        # Get the exigible move lines ids instead of the recordset to increase
        # performance with a large number of journal items
        move_lines_exigible_ids = set(
            self.env["account.move.line"]
            .search(
                self._get_move_lines_domain(move_ids, wizard, journal_ids)
                + self.env["account.move.line"]._get_tax_exigible_domain(),
            )
            .ids
        )
        move_line_ids_taxes_data = {}
        if move_lines:
            # Get the taxes ids for the move lines
            query_taxes_params = self._get_query_taxes_params(move_lines)
            query_taxes = self._get_query_taxes()
            self.env.cr.execute(query_taxes, query_taxes_params)
            # Fetch the taxes associated to the move line
            for (
                move_line_id,
                account_tax_id,
                tax_description,
                tax_name,
            ) in self.env.cr.fetchall():
                if move_line_id not in move_line_ids_taxes_data.keys():
                    move_line_ids_taxes_data[move_line_id] = {}
                move_line_ids_taxes_data[move_line_id][account_tax_id] = {
                    "name": tax_name,
                    "description": tax_description,
                }
        Move_Lines = {}
        auto_sequence = len(move_ids)
        Move_Lines = defaultdict(list)
        for ml in move_lines:
            move_id = ml.move_id.id
            if move_id not in Move_Lines:
                auto_sequence -= 1
            taxes = move_line_ids_taxes_data.get(ml.id, {})
            # Check the exigibility of the move line by id
            # this way we avoid the recreation of the recordset which affects to the
            # performance in the case of a large number of journal items
            exigible = ml.id in move_lines_exigible_ids
            Move_Lines[move_id].append(
                self._get_move_lines_data(ml, wizard, taxes, auto_sequence, exigible)
            )
        account_ids_data = self._get_account_data(move_lines.account_id)
        partner_ids_data = self._get_partner_data(move_lines.partner_id)
        currency_ids_data = self._get_currency_data(move_lines.currency_id)
        tax_line_ids_data = self._get_tax_line_data(move_lines.tax_line_id)
        return (
            move_lines.ids,
            Move_Lines,
            account_ids_data,
            partner_ids_data,
            currency_ids_data,
            tax_line_ids_data,
            move_line_ids_taxes_data,
        )

    def _get_journal_tax_lines(self, wizard, moves_data):
        journals_taxes_data = {}
        for move_data in moves_data:
            report_move_lines = move_data["report_move_lines"]
            for report_move_line in report_move_lines:
                ml_data = report_move_line
                tax_ids = []
                if ml_data["tax_line_id"]:
                    tax_ids.append(ml_data["tax_line_id"])
                if ml_data["tax_ids"]:
                    tax_ids += ml_data["tax_ids"]
                tax_ids = list(set(tax_ids))
                journal_id = ml_data["journal_id"]
                if journal_id not in journals_taxes_data.keys():
                    journals_taxes_data[journal_id] = {}
                taxes = self.env["account.tax"].search_fetch(
                    [("id", "in", tax_ids)], ["name", "description"]
                )
                for tax in taxes:
                    if tax.id not in journals_taxes_data[journal_id]:
                        journals_taxes_data[journal_id][tax.id] = {
                            "base_debit": 0.0,
                            "base_credit": 0.0,
                            "base_balance": 0.0,
                            "tax_debit": 0.0,
                            "tax_credit": 0.0,
                            "tax_balance": 0.0,
                            "tax_name": tax.name,
                            "tax_code": tax.description,
                        }
                    field_keys = [
                        "base_debit",
                        "base_credit",
                        "base_balance",
                        "tax_debit",
                        "tax_credit",
                        "tax_balance",
                    ]
                    for field_key in field_keys:
                        journals_taxes_data[journal_id][tax.id][field_key] += ml_data[
                            field_key
                        ]
        journals_taxes_data_2 = {}
        for journal_id in journals_taxes_data.keys():
            journals_taxes_data_2[journal_id] = []
            for tax_id in journals_taxes_data[journal_id].keys():
                journals_taxes_data_2[journal_id] += [
                    journals_taxes_data[journal_id][tax_id]
                ]
        return journals_taxes_data_2

    def _get_report_values(self, docids, data):
        wizard_id = data["wizard_id"]
        wizard = self.env["journal.ledger.report.wizard"].browse(wizard_id)
        company = self.env["res.company"].browse(data["company_id"])
        journal_ids = data["journal_ids"]
        journal_ledgers_data = self._get_journal_ledgers(wizard, journal_ids, company)
        move_ids, moves_data, move_ids_data = self._get_moves(wizard, journal_ids)
        journal_moves_data = {}
        for key, items in itertools.groupby(
            moves_data, operator.itemgetter("journal_id")
        ):
            if key not in journal_moves_data.keys():
                journal_moves_data[key] = []
            journal_moves_data[key] += list(items)
        move_lines_data = account_ids_data = partner_ids_data = currency_ids_data = (
            tax_line_ids_data
        ) = move_line_ids_taxes_data = {}
        if move_ids:
            move_lines = self._get_move_lines(move_ids, wizard, journal_ids)
            move_lines_data = move_lines[1]
            account_ids_data = move_lines[2]
            partner_ids_data = move_lines[3]
            currency_ids_data = move_lines[4]
            tax_line_ids_data = move_lines[5]
        for move_data in moves_data:
            move_id = move_data["move_id"]
            move_data["report_move_lines"] = []
            if move_id in move_lines_data.keys():
                move_data["report_move_lines"] += move_lines_data[move_id]
        journals_taxes_data = {}
        if moves_data:
            journals_taxes_data = self._get_journal_tax_lines(wizard, moves_data)
        for journal_ledger_data in journal_ledgers_data:
            journal_id = journal_ledger_data["id"]
            journal_ledger_data["tax_lines"] = journals_taxes_data.get(journal_id, [])
        journal_totals = {}
        for move_id in move_lines_data.keys():
            for move_line_data in move_lines_data[move_id]:
                journal_id = move_line_data["journal_id"]
                if journal_id not in journal_totals.keys():
                    journal_totals[journal_id] = {"debit": 0.0, "credit": 0.0}
                for item in ["debit", "credit"]:
                    journal_totals[journal_id][item] += move_line_data[item]
        for journal_ledger_data in journal_ledgers_data:
            journal_id = journal_ledger_data["id"]
            if journal_id in journal_moves_data.keys():
                journal_ledger_data["report_moves"] = journal_moves_data[journal_id]
            else:
                journal_ledger_data["report_moves"] = []
            if journal_id in journal_totals.keys():
                for item in ["debit", "credit"]:
                    journal_ledger_data[item] += journal_totals[journal_id][item]
        return {
            "doc_ids": [wizard_id],
            "doc_model": "journal.ledger.report.wizard",
            "docs": self.env["journal.ledger.report.wizard"].browse(wizard_id),
            "group_option": data["group_option"],
            "foreign_currency": data["foreign_currency"],
            "with_account_name": data["with_account_name"],
            "company_name": company.display_name,
            "currency_name": company.currency_id.name,
            "date_from": data["date_from"],
            "date_to": data["date_to"],
            "move_target": data["move_target"],
            "with_auto_sequence": data["with_auto_sequence"],
            "account_ids_data": account_ids_data,
            "partner_ids_data": partner_ids_data,
            "currency_ids_data": currency_ids_data,
            "move_ids_data": move_ids_data,
            "tax_line_data": tax_line_ids_data,
            "move_line_ids_taxes_data": move_line_ids_taxes_data,
            "Journal_Ledgers": journal_ledgers_data,
            "Moves": moves_data,
        }
