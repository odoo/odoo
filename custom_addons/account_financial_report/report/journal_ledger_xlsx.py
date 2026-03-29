# Author: Damien Crier
# Author: Julien Coux
# Copyright 2016 Camptocamp SA
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models


class JournalLedgerXslx(models.AbstractModel):
    _name = "report.a_f_r.report_journal_ledger_xlsx"
    _description = "Journal Ledger XLSX Report"
    _inherit = "report.account_financial_report.abstract_report_xlsx"

    def _get_report_name(self, report, data=False):
        company_id = data.get("company_id", False)
        report_name = _("Journal Ledger")
        if company_id:
            company = self.env["res.company"].browse(company_id)
            suffix = f" - {company.name} - {company.currency_id.name}"
            report_name = report_name + suffix
        return report_name

    def _get_report_columns(self, report):
        columns = [
            {"header": _("Entry"), "field": "entry", "width": 18},
            {"header": _("Date"), "field": "date", "width": 11},
            {"header": _("Account"), "field": "account_code", "width": 9},
        ]

        if report.with_auto_sequence:
            columns.insert(
                0, {"header": _("Sequence"), "field": "auto_sequence", "width": 10}
            )

        if report.with_account_name:
            columns.append(
                {"header": _("Account Name"), "field": "account_name", "width": 15}
            )

        columns += [
            {"header": _("Partner"), "field": "partner", "width": 25},
            {"header": _("Ref - Label"), "field": "label", "width": 40},
            {"header": _("Taxes"), "field": "taxes_description", "width": 11},
            {"header": _("Debit"), "field": "debit", "type": "amount", "width": 14},
            {"header": _("Credit"), "field": "credit", "type": "amount", "width": 14},
        ]

        if report.foreign_currency:
            columns += [
                {
                    "header": _("Currency"),
                    "field": "currency_name",
                    "width": 14,
                    "type": "currency_name",
                },
                {
                    "header": _("Amount Currency"),
                    "field": "amount_currency",
                    "type": "amount",
                    "width": 18,
                },
            ]

        columns_as_dict = {}
        for i, column in enumerate(columns):
            columns_as_dict[i] = column
        return columns_as_dict

    def _get_journal_tax_columns(self, report):
        return {
            0: {"header": _("Name"), "field": "tax_name", "width": 35},
            1: {"header": _("Description"), "field": "tax_code", "width": 18},
            2: {
                "header": _("Base Debit"),
                "field": "base_debit",
                "type": "amount",
                "width": 14,
            },
            3: {
                "header": _("Base Credit"),
                "field": "base_credit",
                "type": "amount",
                "width": 14,
            },
            4: {
                "header": _("Base Balance"),
                "field": "base_balance",
                "type": "amount",
                "width": 14,
            },
            5: {
                "header": _("Tax Debit"),
                "field": "tax_debit",
                "type": "amount",
                "width": 14,
            },
            6: {
                "header": _("Tax Credit"),
                "field": "tax_credit",
                "type": "amount",
                "width": 14,
            },
            7: {
                "header": _("Tax Balance"),
                "field": "tax_balance",
                "type": "amount",
                "width": 14,
            },
        }

    def _get_col_count_filter_name(self):
        return 2

    def _get_col_count_filter_value(self):
        return 3

    def _get_report_filters(self, report):
        target_label_by_value = {
            value: label
            for value, label in self.env[
                "journal.ledger.report.wizard"
            ]._get_move_targets()
        }

        sort_option_label_by_value = {
            value: label
            for value, label in self.env[
                "journal.ledger.report.wizard"
            ]._get_sort_options()
        }

        return [
            [_("Company"), report.company_id.name],
            [
                _("Date range filter"),
                _("From: %(date_from)s To: %(date_to)s")
                % ({"date_from": report.date_from, "date_to": report.date_to}),
            ],
            [
                _("Target moves filter"),
                _("%s") % target_label_by_value[report.move_target],
            ],
            [
                _("Entries sorted by"),
                _("%s") % sort_option_label_by_value[report.sort_option],
            ],
            [
                _("Journals"),
                ", ".join(
                    [
                        f"{report_journal.code} - {report_journal.name}"
                        for report_journal in report.journal_ids
                    ]
                ),
            ],
        ]

    def _generate_report_content(self, workbook, report, data, report_data):
        res_data = self.env[
            "report.account_financial_report.journal_ledger"
        ]._get_report_values(report, data)
        group_option = report.group_option
        if group_option == "journal":
            for ledger in res_data["Journal_Ledgers"]:
                self._generate_journal_content(
                    workbook, report, res_data, ledger, report_data
                )
        elif group_option == "none":
            self._generate_no_group_content(workbook, report, res_data, report_data)

    def _generate_no_group_content(self, workbook, report, res_data, report_data):
        self._generate_moves_content(
            workbook, "Report", report, res_data, res_data["Moves"], report_data
        )
        self._generate_no_group_taxes_summary(workbook, report, res_data, report_data)

    def _generate_journal_content(
        self, workbook, report, res_data, ledger, report_data
    ):
        journal = self.env["account.journal"].browse(ledger["id"])
        currency_name = (
            journal.currency_id
            and journal.currency_id.name
            or journal.company_id.currency_id.name
        )
        sheet_name = f"{journal.code} ({currency_name}) - {journal.name}"
        self._generate_moves_content(
            workbook, sheet_name, report, res_data, ledger["report_moves"], report_data
        )
        self._generate_journal_taxes_summary(workbook, ledger, report_data)

    def _generate_no_group_taxes_summary(self, workbook, report, res_data, report_data):
        self._generate_taxes_summary(
            workbook, "Tax Report", res_data["tax_line_data"], report_data
        )

    def _generate_journal_taxes_summary(self, workbook, ledger, report_data):
        journal = self.env["account.journal"].browse(ledger["id"])
        currency_name = (
            journal.currency_id
            and journal.currency_id.name
            or journal.company_id.currency_id.name
        )
        sheet_name = f"Tax - {journal.code} ({currency_name}) - {journal.name}"
        self._generate_taxes_summary(
            workbook, sheet_name, ledger["tax_lines"], report_data
        )

    def _generate_moves_content(
        self, workbook, sheet_name, report, res_data, moves, report_data
    ):
        report_data["workbook"] = workbook
        report_data["sheet"] = workbook.add_worksheet(sheet_name)
        self._set_column_width(report_data)

        report_data["row_pos"] = 1

        self.write_array_title(sheet_name, report_data)
        report_data["row_pos"] += 2

        self.write_array_header(report_data)
        account_ids_data = res_data["account_ids_data"]
        partner_ids_data = res_data["partner_ids_data"]
        currency_ids_data = res_data["currency_ids_data"]
        move_ids_data = res_data["move_ids_data"]
        for move in moves:
            for line in move["report_move_lines"]:
                currency_data = currency_ids_data.get(line["currency_id"], False)
                currency_name = currency_data and currency_data["name"] or ""
                account_data = account_ids_data.get(line["account_id"], False)
                account_name = account_data and account_data["name"] or ""
                account_code = account_data and account_data["code"] or ""
                move_data = move_ids_data.get(line["move_id"], False)
                move_entry = move_data and move_data["entry"] or ""
                line["partner"] = self._get_partner_name(
                    line["partner_id"], partner_ids_data
                )
                line["auto_sequence"] = line["auto_sequence"]
                line["account_code"] = account_code
                line["account_name"] = account_name
                line["currency_name"] = currency_name
                line["entry"] = move_entry
                line["taxes_description"] = report._get_ml_tax_description(
                    line,
                    res_data["tax_line_data"].get(line["tax_line_id"]),
                    res_data["move_line_ids_taxes_data"].get(
                        line["move_line_id"], False
                    ),
                )
                self.write_line_from_dict(line, report_data)
            report_data["row_pos"] += 1

    def _generate_taxes_summary(
        self, workbook, sheet_name, tax_lines_dict, report_data
    ):
        report_data["workbook"] = workbook
        report_data["sheet"] = workbook.add_worksheet(sheet_name)

        report_data["row_pos"] = 1
        self.write_array_title(sheet_name, report_data)
        report_data["row_pos"] += 2

    def _get_partner_name(self, partner_id, partner_data):
        if partner_id in partner_data.keys():
            return partner_data[partner_id]["name"]
        else:
            return ""
