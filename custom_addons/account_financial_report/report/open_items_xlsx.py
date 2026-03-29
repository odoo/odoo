# Author: Julien Coux
# Copyright 2016 Camptocamp SA
# Copyright 2021 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, models


class OpenItemsXslx(models.AbstractModel):
    _name = "report.a_f_r.report_open_items_xlsx"
    _description = "Open Items XLSX Report"
    _inherit = "report.account_financial_report.abstract_report_xlsx"

    def _get_report_name(self, report, data=False):
        company_id = data.get("company_id", False)
        report_name = _("Open Items")
        if company_id:
            company = self.env["res.company"].browse(company_id)
            suffix = f" - {company.name} - {company.currency_id.name}"
            report_name = report_name + suffix
        return report_name

    def _get_report_columns(self, report):
        res = {
            0: {"header": _("Date"), "field": "date", "width": 11},
            1: {"header": _("Entry"), "field": "move_name", "width": 18},
            2: {"header": _("Journal"), "field": "journal", "width": 8},
            3: {"header": _("Account"), "field": "account", "width": 9},
            4: {"header": _("Partner"), "field": "partner_name", "width": 25},
            5: {"header": _("Ref - Label"), "field": "ref_label", "width": 40},
            6: {"header": _("Due date"), "field": "date_maturity", "width": 11},
            7: {
                "header": _("Original"),
                "field": "original",
                "type": "amount",
                "width": 14,
            },
            8: {
                "header": _("Residual"),
                "field": "amount_residual",
                "field_final_balance": "residual",
                "type": "amount",
                "width": 14,
            },
        }
        if report.foreign_currency:
            foreign_currency = {
                9: {
                    "header": _("Cur."),
                    "field": "currency_name",
                    "field_currency_balance": "currency_name",
                    "type": "currency_name",
                    "width": 7,
                },
                10: {
                    "header": _("Cur. Original"),
                    "field": "amount_currency",
                    "field_final_balance": "amount_currency",
                    "type": "amount_currency",
                    "width": 14,
                },
                11: {
                    "header": _("Cur. Residual"),
                    "field": "amount_residual_currency",
                    "field_final_balance": "amount_currency",
                    "type": "amount_currency",
                    "width": 14,
                },
            }
            res = {**res, **foreign_currency}
        return res

    def _get_report_filters(self, report):
        return [
            [_("Date at filter"), report.date_at.strftime("%d/%m/%Y")],
            [
                _("Target moves filter"),
                _("All posted entries")
                if report.target_move == "posted"
                else _("All entries"),
            ],
            [
                _("Account balance at 0 filter"),
                _("Hide") if report.hide_account_at_0 else _("Show"),
            ],
            [
                _("Show foreign currency"),
                _("Yes") if report.foreign_currency else _("No"),
            ],
        ]

    def _get_col_count_filter_name(self):
        return 2

    def _get_col_count_filter_value(self):
        return 2

    def _get_col_count_final_balance_name(self):
        return 5

    def _get_col_pos_final_balance_label(self):
        return 5

    def _calculate_amounts_by_partner(self, account_id, open_items_move_lines_data):
        total_amount = {}
        for line in open_items_move_lines_data:
            partner_id_key = line["partner_id"]
            if account_id not in total_amount:
                total_amount[account_id] = {}
            if partner_id_key not in total_amount[account_id]:
                total_amount[account_id][partner_id_key] = {"residual": 0.0}
            total_amount[account_id][partner_id_key]["residual"] += line[
                "amount_residual"
            ]
        return total_amount

    def _generate_report_content_by_salesperson(
        self, workbook, report, data, report_data, res_data
    ):
        Open_items = res_data["Open_Items"]
        accounts_data = res_data["accounts_data"]
        partners_data = res_data["partners_data"]
        journals_data = res_data["journals_data"]
        total_amount = res_data["total_amount"]

        for partner_id in partners_data.keys():
            # Create a new sheet for each partner
            partner_totals = {}
            partner_name = partners_data[partner_id]["name"]
            new_sheet = workbook.add_worksheet(partner_name[:31])
            report_data["sheet"] = new_sheet
            report_data["row_pos"] = 0

            for account_id in Open_items.keys():
                if partner_id in Open_items[account_id]:
                    self.write_array_title(
                        accounts_data[account_id]["code"]
                        + " - "
                        + accounts_data[account_id]["name"],
                        report_data,
                    )

                    # For each partner
                    if Open_items[account_id]:
                        type_object = "partner"
                        # Write partner title
                        self.write_array_title(
                            partners_data[partner_id]["name"], report_data
                        )

                        # Calculate totals by partner_id
                        partner_totals = self._calculate_amounts_by_partner(
                            account_id, Open_items[account_id][partner_id]
                        )
                        # Display array header for move lines
                        self.write_array_header(report_data)
                        # Display account move lines
                        has_lines = False
                        for partner_id_key, total_amount_dict in partner_totals.get(
                            account_id, {}
                        ).items():
                            for line in Open_items[account_id][partner_id]:
                                if line["partner_id"] == partner_id_key:
                                    line.update(
                                        {
                                            "account": accounts_data[account_id][
                                                "code"
                                            ],
                                            "journal": journals_data[
                                                line["journal_id"]
                                            ]["code"],
                                        }
                                    )
                                    self.write_line_from_dict(line, report_data)
                                    has_lines = True
                            if has_lines:
                                partner = self.env["res.partner"].browse(partner_id_key)
                                # Display ending balance line for partner
                                partner_data = {
                                    "id": partner_id_key,
                                    "name": partner.name
                                    if partner
                                    else _("Missing Partner"),
                                    "currency_id": accounts_data[account_id][
                                        "currency_id"
                                    ],
                                    "currency_name": accounts_data[account_id][
                                        "currency_name"
                                    ],
                                    "residual": total_amount_dict,
                                }
                                self.write_ending_balance_from_dict(
                                    partner_data,
                                    "partner_subtotal",
                                    partner_totals,
                                    report_data,
                                    account_id=account_id,
                                    partner_id=partner_id_key,
                                )
                                has_lines = False
                        # Display ending balance line for salesperson
                        partners_data[partner_id].update(
                            {
                                "currency_id": accounts_data[account_id]["currency_id"],
                                "currency_name": accounts_data[account_id][
                                    "currency_name"
                                ],
                            }
                        )
                        self.write_ending_balance_from_dict(
                            partners_data[partner_id],
                            type_object,
                            total_amount,
                            report_data,
                            account_id=account_id,
                            partner_id=partner_id,
                        )
                        # Line break
                        report_data["row_pos"] += 1

    def _generate_report_content_by_partner(
        self, workbook, report, data, report_data, res_data
    ):
        Open_items = res_data["Open_Items"]
        accounts_data = res_data["accounts_data"]
        partners_data = res_data["partners_data"]
        journals_data = res_data["journals_data"]
        total_amount = res_data["total_amount"]
        show_partner_details = res_data["show_partner_details"]
        for account_id in Open_items.keys():
            # Write account title
            self.write_array_title(
                accounts_data[account_id]["code"]
                + " - "
                + accounts_data[account_id]["name"],
                report_data,
            )
            # For each partner
            if Open_items[account_id]:
                if show_partner_details:
                    for partner_id in Open_items[account_id]:
                        type_object = "partner"
                        # Write partner title
                        self.write_array_title(
                            partners_data[partner_id]["name"], report_data
                        )

                        # Display array header for move lines
                        self.write_array_header(report_data)

                        # Display account move lines
                        for line in Open_items[account_id][partner_id]:
                            line.update(
                                {
                                    "account": accounts_data[account_id]["code"],
                                    "journal": journals_data[line["journal_id"]][
                                        "code"
                                    ],
                                }
                            )
                            self.write_line_from_dict(line, report_data)

                        # Display ending balance line for partner
                        partners_data[partner_id].update(
                            {
                                "currency_id": accounts_data[account_id]["currency_id"],
                                "currency_name": accounts_data[account_id][
                                    "currency_name"
                                ],
                            }
                        )
                        self.write_ending_balance_from_dict(
                            partners_data[partner_id],
                            type_object,
                            total_amount,
                            report_data,
                            account_id=account_id,
                            partner_id=partner_id,
                        )

                        # Line break
                        report_data["row_pos"] += 1
                else:
                    # Display array header for move lines
                    self.write_array_header(report_data)

                    # Display account move lines
                    for line in Open_items[account_id]:
                        line.update(
                            {
                                "account": accounts_data[account_id]["code"],
                                "journal": journals_data[line["journal_id"]]["code"],
                            }
                        )
                        self.write_line_from_dict(line, report_data)

                    # Display ending balance line for account
                    type_object = "account"
                    self.write_ending_balance_from_dict(
                        accounts_data[account_id],
                        type_object,
                        total_amount,
                        report_data,
                        account_id=account_id,
                    )

                    # 2 lines break
                    report_data["row_pos"] += 2

    def _generate_report_content(self, workbook, report, data, report_data):
        res_data = self.env[
            "report.account_financial_report.open_items"
        ]._get_report_values(report, data)
        show_partner_details = res_data["show_partner_details"]
        grouped_by = res_data["grouped_by"]
        if grouped_by == "salesperson" and show_partner_details:
            return self._generate_report_content_by_salesperson(
                workbook, report, data, report_data, res_data
            )
        else:
            return self._generate_report_content_by_partner(
                workbook, report, data, report_data, res_data
            )

    def write_ending_balance_from_dict(
        self,
        my_object,
        type_object,
        total_amount,
        report_data,
        account_id=False,
        partner_id=False,
    ):
        """Specific function to write ending balance for Open Items"""
        if type_object == "partner":
            name = my_object["name"]
            my_object["residual"] = total_amount[account_id][partner_id]["residual"]
            label = _("Partner ending balance")
        elif type_object == "account":
            name = my_object["code"] + " - " + my_object["name"]
            my_object["residual"] = total_amount[account_id]["residual"]
            label = _("Ending balance")
        elif type_object == "partner_subtotal":
            name = my_object["name"]
            my_object["residual"] = total_amount[account_id][partner_id]["residual"]
            label = _("Ending balance")
        return super().write_ending_balance_from_dict(
            my_object, name, label, report_data
        )
