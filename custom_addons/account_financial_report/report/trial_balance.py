# © 2016 Julien Coux (Camptocamp)
# © 2018 Forest and Biomass Romania SA
# Copyright 2020 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class TrialBalanceReport(models.AbstractModel):
    _name = "report.account_financial_report.trial_balance"
    _description = "Trial Balance Report"
    _inherit = "report.account_financial_report.abstract_report"

    def _get_initial_balances_bs_ml_domain(
        self,
        account_ids,
        journal_ids,
        partner_ids,
        company_id,
        date_from,
        only_posted_moves,
        show_partner_details,
    ):
        accounts_domain = [
            ("company_ids", "in", [company_id]),
            ("include_initial_balance", "=", True),
        ]
        if account_ids:
            accounts_domain += [("id", "in", account_ids)]
        domain = [("date", "<", date_from)]
        accounts = self.env["account.account"].search(accounts_domain)
        domain += [("account_id", "in", accounts.ids)]
        if company_id:
            domain += [("company_id", "=", company_id)]
        if journal_ids:
            domain += [("journal_id", "in", journal_ids)]
        if partner_ids:
            domain += [("partner_id", "in", partner_ids)]
        if only_posted_moves:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["posted", "draft"])]
        if show_partner_details:
            domain += [
                (
                    "account_id.account_type",
                    "in",
                    ["asset_receivable", "liability_payable"],
                )
            ]
        return domain

    def _get_initial_balances_pl_ml_domain(
        self,
        account_ids,
        journal_ids,
        partner_ids,
        company_id,
        date_from,
        only_posted_moves,
        show_partner_details,
        fy_start_date,
    ):
        accounts_domain = [
            ("company_ids", "in", [company_id]),
            ("include_initial_balance", "=", False),
        ]
        if account_ids:
            accounts_domain += [("id", "in", account_ids)]
        domain = [("date", "<", date_from), ("date", ">=", fy_start_date)]
        accounts = self.env["account.account"].search(accounts_domain)
        domain += [("account_id", "in", accounts.ids)]
        if company_id:
            domain += [("company_id", "=", company_id)]
        if journal_ids:
            domain += [("journal_id", "in", journal_ids)]
        if partner_ids:
            domain += [("partner_id", "in", partner_ids)]
        if only_posted_moves:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["posted", "draft"])]
        if show_partner_details:
            domain += [
                (
                    "account_id.account_type",
                    "in",
                    ["asset_receivable", "liability_payable"],
                )
            ]
        return domain

    @api.model
    def _get_period_ml_domain(
        self,
        account_ids,
        journal_ids,
        partner_ids,
        company_id,
        date_to,
        date_from,
        only_posted_moves,
        show_partner_details,
    ):
        domain = [
            ("display_type", "not in", ["line_note", "line_section"]),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        if company_id:
            domain += [("company_id", "=", company_id)]
        if account_ids:
            domain += [("account_id", "in", account_ids)]
        if journal_ids:
            domain += [("journal_id", "in", journal_ids)]
        if partner_ids:
            domain += [("partner_id", "in", partner_ids)]
        if only_posted_moves:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["posted", "draft"])]
        if show_partner_details:
            domain += [
                (
                    "account_id.account_type",
                    "in",
                    ["asset_receivable", "liability_payable"],
                )
            ]
        return domain

    def _get_initial_balance_fy_pl_ml_domain(
        self,
        account_ids,
        journal_ids,
        partner_ids,
        company_id,
        fy_start_date,
        only_posted_moves,
        show_partner_details,
    ):
        accounts_domain = [
            ("company_ids", "in", [company_id]),
            ("include_initial_balance", "=", False),
        ]
        if account_ids:
            accounts_domain += [("id", "in", account_ids)]
        domain = [("date", "<", fy_start_date)]
        accounts = self.env["account.account"].search(accounts_domain)
        domain += [("account_id", "in", accounts.ids)]
        if company_id:
            domain += [("company_id", "=", company_id)]
        if journal_ids:
            domain += [("journal_id", "in", journal_ids)]
        if partner_ids:
            domain += [("partner_id", "in", partner_ids)]
        if only_posted_moves:
            domain += [("move_id.state", "=", "posted")]
        else:
            domain += [("move_id.state", "in", ["posted", "draft"])]
        if show_partner_details:
            domain += [
                (
                    "account_id.account_type",
                    "in",
                    ["asset_receivable", "liability_payable"],
                )
            ]
        return domain

    def _get_pl_initial_balance(
        self,
        account_ids,
        journal_ids,
        partner_ids,
        company_id,
        fy_start_date,
        only_posted_moves,
        show_partner_details,
        foreign_currency,
    ):
        domain = self._get_initial_balance_fy_pl_ml_domain(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            fy_start_date,
            only_posted_moves,
            show_partner_details,
        )
        initial_balances = self.env["account.move.line"].read_group(
            domain=domain,
            fields=["account_id", "balance", "amount_currency:sum"],
            groupby=["account_id", "currency_id"],
        )
        pl_initial_balance = 0.0
        pl_initial_currency_balance = 0.0
        for initial_balance in initial_balances:
            pl_initial_balance += initial_balance["balance"]
            if foreign_currency:
                pl_initial_currency_balance += round(
                    initial_balance["amount_currency"], 2
                )
        return pl_initial_balance, pl_initial_currency_balance

    @api.model
    def _compute_account_amount(
        self, total_amount, tb_initial_acc, tb_period_acc, foreign_currency
    ):
        for tb in tb_period_acc:
            acc_id = tb["account_id"][0]
            total_amount[acc_id] = self._prepare_total_amount(tb, foreign_currency)
            total_amount[acc_id]["credit"] = tb["credit"]
            total_amount[acc_id]["debit"] = tb["debit"]
            total_amount[acc_id]["balance"] = tb["balance"]
            total_amount[acc_id]["initial_balance"] = 0.0
            if foreign_currency:
                total_amount[acc_id]["initial_currency_balance"] = 0.0
            if "__context" in tb and "group_by" in tb["__context"]:
                group_by = tb["__context"]["group_by"][0]
                gb_data = {}
                tb_grouped = self.env["account.move.line"].read_group(
                    domain=tb["__domain"],
                    fields=[
                        group_by,
                        "debit",
                        "credit",
                        "balance",
                        "amount_currency:sum",
                    ],
                    groupby=[group_by],
                )
                for tb2 in tb_grouped:
                    gb_id = tb2[group_by][0] if tb2[group_by] else 0
                    gb_data[gb_id] = self._prepare_total_amount(tb2, foreign_currency)
                    gb_data[gb_id]["credit"] = tb2["credit"]
                    gb_data[gb_id]["debit"] = tb2["debit"]
                    gb_data[gb_id]["balance"] = tb2["balance"]
                    gb_data[gb_id]["initial_balance"] = 0.0
                    if foreign_currency:
                        gb_data[gb_id]["initial_currency_balance"] = 0.0
                total_amount[acc_id]["group_by"] = group_by
                total_amount[acc_id]["group_by_data"] = gb_data
        for tb in tb_initial_acc:
            acc_id = tb["account_id"]
            if acc_id not in total_amount.keys():
                total_amount[acc_id] = self._prepare_total_amount(tb, foreign_currency)
                total_amount[acc_id]["group_by_data"] = {}
                total_amount[acc_id]["group_by_data"][0] = self._prepare_total_amount(
                    tb, foreign_currency
                )
            else:
                total_amount[acc_id]["initial_balance"] = tb["balance"]
                total_amount[acc_id]["ending_balance"] += tb["balance"]
                if foreign_currency:
                    total_amount[acc_id]["initial_currency_balance"] = round(
                        tb["amount_currency"], 2
                    )
                    total_amount[acc_id]["ending_currency_balance"] += round(
                        tb["amount_currency"], 2
                    )
                if "group_by_data" in tb:
                    for gb_key in list(tb["group_by_data"]):
                        tb2 = tb["group_by_data"][gb_key]
                        if "group_by_data" in total_amount[acc_id]:
                            if gb_key not in total_amount[acc_id]["group_by_data"]:
                                total_amount[acc_id]["group_by_data"][gb_key] = (
                                    self._prepare_total_amount(tb2, foreign_currency)
                                )
                            else:
                                total_amount[acc_id]["group_by_data"][gb_key][
                                    "initial_balance"
                                ] = tb2["balance"]
                                total_amount[acc_id]["group_by_data"][gb_key][
                                    "ending_balance"
                                ] += tb2["balance"]
                                if foreign_currency:
                                    total_amount[acc_id]["group_by_data"][gb_key][
                                        "initial_currency_balance"
                                    ] = round(tb2["amount_currency"], 2)
                                    total_amount[acc_id]["group_by_data"][gb_key][
                                        "ending_currency_balance"
                                    ] += round(tb2["amount_currency"], 2)
        return total_amount

    @api.model
    def _prepare_total_amount(self, tb, foreign_currency):
        res = {
            "credit": 0.0,
            "debit": 0.0,
            "balance": 0.0,
            "initial_balance": tb["balance"],
            "ending_balance": tb["balance"],
        }
        if foreign_currency:
            res["initial_currency_balance"] = round(tb["amount_currency"], 2)
            res["ending_currency_balance"] = round(tb["amount_currency"], 2)
        return res

    @api.model
    def _compute_acc_prt_amount(
        self, total_amount, tb, acc_id, prt_id, foreign_currency
    ):
        # Add keys to dict if not exists
        if acc_id not in total_amount:
            total_amount[acc_id] = self._prepare_total_amount(tb, foreign_currency)
        if prt_id not in total_amount[acc_id]:
            total_amount[acc_id][prt_id] = self._prepare_total_amount(
                tb, foreign_currency
            )
        else:
            # Increase balance field values
            total_amount[acc_id][prt_id]["initial_balance"] = tb["balance"]
            total_amount[acc_id][prt_id]["ending_balance"] += tb["balance"]
            if foreign_currency:
                total_amount[acc_id][prt_id]["initial_currency_balance"] = round(
                    tb["amount_currency"], 2
                )
                total_amount[acc_id][prt_id]["ending_currency_balance"] += round(
                    tb["amount_currency"], 2
                )
        total_amount[acc_id][prt_id]["partner_name"] = (
            tb["partner_id"][1] if tb["partner_id"] else _("Missing Partner")
        )
        return total_amount

    @api.model
    def _compute_partner_amount(
        self, total_amount, tb_initial_prt, tb_period_prt, foreign_currency
    ):
        partners_ids = set()
        partners_data = {}
        for tb in tb_period_prt:
            acc_id = tb["account_id"][0]
            prt_id = tb["partner_id"][0] if tb["partner_id"] else 0
            if prt_id not in partners_ids:
                partner_name = (
                    tb["partner_id"][1] if tb["partner_id"] else _("Missing Partner")
                )
                partners_data.update({prt_id: {"id": prt_id, "name": partner_name}})
            total_amount[acc_id][prt_id] = self._prepare_total_amount(
                tb, foreign_currency
            )
            total_amount[acc_id][prt_id]["credit"] = tb["credit"]
            total_amount[acc_id][prt_id]["debit"] = tb["debit"]
            total_amount[acc_id][prt_id]["balance"] = tb["balance"]
            total_amount[acc_id][prt_id]["initial_balance"] = 0.0
            total_amount[acc_id][prt_id]["partner_name"] = partners_data[prt_id]["name"]
            partners_ids.add(prt_id)
        for tb in tb_initial_prt:
            acc_id = tb["account_id"][0]
            prt_id = tb["partner_id"][0] if tb["partner_id"] else 0
            if prt_id not in partners_ids:
                partner_name = (
                    tb["partner_id"][1] if tb["partner_id"] else _("Missing Partner")
                )
                partners_data.update({prt_id: {"id": prt_id, "name": partner_name}})
            total_amount = self._compute_acc_prt_amount(
                total_amount, tb, acc_id, prt_id, foreign_currency
            )
        # sort on partner_name
        for acc_id, total_data in total_amount.items():
            tmp_list = sorted(
                total_data.items(),
                key=lambda x: isinstance(x[0], int)
                and isinstance(x[1], dict)
                and x[1]["partner_name"]
                or x[0],
            )
            total_amount[acc_id] = {}
            for key, value in tmp_list:
                total_amount[acc_id][key] = value
        return total_amount, partners_data

    def _remove_accounts_at_cero(self, total_amount, show_partner_details, company):
        def is_removable(d):
            rounding = company.currency_id.rounding
            return (
                float_is_zero(d["initial_balance"], precision_rounding=rounding)
                and float_is_zero(d["credit"], precision_rounding=rounding)
                and float_is_zero(d["debit"], precision_rounding=rounding)
                and float_is_zero(d["ending_balance"], precision_rounding=rounding)
            )

        accounts_to_remove = []
        for acc_id, ta_data in total_amount.items():
            if is_removable(ta_data):
                accounts_to_remove.append(acc_id)
            elif show_partner_details:
                partner_to_remove = []
                for key, value in ta_data.items():
                    # If the show_partner_details option is checked,
                    # the partner data is in the same account data dict
                    # but with the partner id as the key
                    if isinstance(key, int) and is_removable(value):
                        partner_to_remove.append(key)
                for partner_id in partner_to_remove:
                    del ta_data[partner_id]
        for account_id in accounts_to_remove:
            del total_amount[account_id]

    # flake8: noqa: C901
    @api.model
    def _get_data(
        self,
        account_ids,
        journal_ids,
        partner_ids,
        company_id,
        date_to,
        date_from,
        foreign_currency,
        only_posted_moves,
        show_partner_details,
        hide_account_at_0,
        unaffected_earnings_account,
        fy_start_date,
        grouped_by,
    ):
        accounts_domain = [("company_ids", "in", [company_id])]
        if account_ids:
            accounts_domain += [("id", "in", account_ids)]
            # If explicit list of accounts is provided,
            # don't include unaffected earnings account
            unaffected_earnings_account = False
        accounts = self.env["account.account"].search(accounts_domain)
        tb_initial_acc = []
        for account in accounts:
            tb_initial_acc.append(
                {"account_id": account.id, "balance": 0.0, "amount_currency": 0.0}
            )
        groupby_fields = ["account_id", "currency_id"]
        if grouped_by:
            groupby_fields.append("analytic_account_ids")
        initial_domain_bs = self._get_initial_balances_bs_ml_domain(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            date_from,
            only_posted_moves,
            show_partner_details,
        )
        tb_initial_acc_bs = self.env["account.move.line"].read_group(
            domain=initial_domain_bs,
            fields=["account_id", "balance", "amount_currency:sum"],
            groupby=groupby_fields,
        )
        initial_domain_pl = self._get_initial_balances_pl_ml_domain(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            date_from,
            only_posted_moves,
            show_partner_details,
            fy_start_date,
        )
        tb_initial_acc_pl = self.env["account.move.line"].read_group(
            domain=initial_domain_pl,
            fields=["account_id", "balance", "amount_currency:sum"],
            groupby=groupby_fields,
        )
        tb_initial_acc_rg = tb_initial_acc_bs + tb_initial_acc_pl
        for account_rg in tb_initial_acc_rg:
            element = list(
                filter(
                    lambda acc_dict: acc_dict["account_id"]
                    == account_rg["account_id"][0],
                    tb_initial_acc,
                )
            )
            if element:
                element[0]["balance"] += account_rg["balance"]
                element[0]["amount_currency"] += account_rg["amount_currency"]
                if "__context" in account_rg and "group_by" in account_rg["__context"]:
                    group_by = account_rg["__context"]["group_by"][0]
                    gb_data = {}
                    account_rg_grouped = self.env["account.move.line"].read_group(
                        domain=account_rg["__domain"],
                        fields=[group_by, "balance", "amount_currency:sum"],
                        groupby=[group_by],
                    )
                    for a_rg2 in account_rg_grouped:
                        gb_id = a_rg2[group_by][0] if a_rg2[group_by] else 0
                        gb_data[gb_id] = {
                            "balance": a_rg2["balance"],
                            "amount_currency": a_rg2["amount_currency"],
                        }
                    element[0]["group_by"] = group_by
                    element[0]["group_by_data"] = gb_data
        if hide_account_at_0:
            tb_initial_acc = [p for p in tb_initial_acc if p["balance"] != 0]

        period_domain = self._get_period_ml_domain(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            date_to,
            date_from,
            only_posted_moves,
            show_partner_details,
        )
        tb_period_acc = self.env["account.move.line"].read_group(
            domain=period_domain,
            fields=["account_id", "debit", "credit", "balance", "amount_currency:sum"],
            groupby=groupby_fields,
        )

        if show_partner_details:
            tb_initial_prt_bs = self.env["account.move.line"].read_group(
                domain=initial_domain_bs,
                fields=["account_id", "partner_id", "balance", "amount_currency:sum"],
                groupby=["account_id", "partner_id", "currency_id"],
                lazy=False,
            )
            tb_initial_prt_pl = self.env["account.move.line"].read_group(
                domain=initial_domain_pl,
                fields=["account_id", "partner_id", "balance", "amount_currency:sum"],
                groupby=["account_id", "partner_id", "currency_id"],
            )
            tb_initial_prt = tb_initial_prt_bs + tb_initial_prt_pl
            if hide_account_at_0:
                tb_initial_prt = [p for p in tb_initial_prt if p["balance"] != 0]
            tb_period_prt = self.env["account.move.line"].read_group(
                domain=period_domain,
                fields=[
                    "account_id",
                    "partner_id",
                    "debit",
                    "credit",
                    "balance",
                    "amount_currency:sum",
                ],
                groupby=["account_id", "currency_id", "partner_id"],
                lazy=False,
            )
        total_amount = {}
        partners_data = []
        total_amount = self._compute_account_amount(
            total_amount, tb_initial_acc, tb_period_acc, foreign_currency
        )
        if show_partner_details:
            total_amount, partners_data = self._compute_partner_amount(
                total_amount, tb_initial_prt, tb_period_prt, foreign_currency
            )
        # Remove accounts a 0 from collections
        if hide_account_at_0:
            company = self.env["res.company"].browse(company_id)
            self._remove_accounts_at_cero(total_amount, show_partner_details, company)

        accounts_ids = list(total_amount.keys())
        unaffected_id = unaffected_earnings_account
        if unaffected_id:
            if unaffected_id not in accounts_ids:
                accounts_ids.append(unaffected_id)
                total_amount[unaffected_id] = {}
                total_amount[unaffected_id]["initial_balance"] = 0.0
                total_amount[unaffected_id]["balance"] = 0.0
                total_amount[unaffected_id]["credit"] = 0.0
                total_amount[unaffected_id]["debit"] = 0.0
                total_amount[unaffected_id]["ending_balance"] = 0.0
                if foreign_currency:
                    total_amount[unaffected_id]["amount_currency"] = 0
                    total_amount[unaffected_id]["initial_currency_balance"] = 0.0
                    total_amount[unaffected_id]["ending_currency_balance"] = 0.0
            if grouped_by:
                total_amount[unaffected_id]["group_by"] = grouped_by
                total_amount[unaffected_id]["group_by_data"] = {}
                # Fix to prevent side effects
                if (
                    foreign_currency
                    and "amount_currency" not in total_amount[unaffected_id]
                ):
                    total_amount[unaffected_id]["amount_currency"] = 0
                group_by_data_item = self._prepare_total_amount(
                    total_amount[unaffected_id], foreign_currency
                )
                total_amount[unaffected_id]["group_by_data"][0] = group_by_data_item
        accounts_data = self._get_accounts_data(accounts_ids)
        (
            pl_initial_balance,
            pl_initial_currency_balance,
        ) = self._get_pl_initial_balance(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            fy_start_date,
            only_posted_moves,
            show_partner_details,
            foreign_currency,
        )
        if unaffected_id:
            total_amount[unaffected_id]["ending_balance"] += pl_initial_balance
            total_amount[unaffected_id]["initial_balance"] += pl_initial_balance
            if foreign_currency:
                total_amount[unaffected_id]["ending_currency_balance"] += (
                    pl_initial_currency_balance
                )
                total_amount[unaffected_id]["initial_currency_balance"] += (
                    pl_initial_currency_balance
                )
            if grouped_by:
                total_amount[unaffected_id]["group_by_data"][0]["ending_balance"] = (
                    total_amount[unaffected_id]["ending_balance"]
                )
                total_amount[unaffected_id]["group_by_data"][0]["initial_balance"] = (
                    total_amount[unaffected_id]["initial_balance"]
                )
                if foreign_currency:
                    total_amount[unaffected_id]["group_by_data"][0][
                        "ending_currency_balance"
                    ] = total_amount[unaffected_id]["ending_currency_balance"]
                    total_amount[unaffected_id]["group_by_data"][0][
                        "initial_currency_balance"
                    ] = total_amount[unaffected_id]["initial_currency_balance"]
        return total_amount, accounts_data, partners_data

    def _get_data_grouped(self, total_amount, accounts_data, foreign_currency):
        """Get the data grouped by analytical account instead of as used
        "without grouping".
        """
        trial_balance = {}
        total_amount_grouped = {"type": "total", "name": _("TOTAL")}
        f_names = [
            "credit",
            "debit",
            "balance",
            "initial_balance",
            "ending_balance",
            "initial_currency_balance",
            "ending_currency_balance",
        ]
        for f_name in f_names:
            total_amount_grouped[f_name] = 0
        for a_id in list(total_amount.keys()):
            for key in list(total_amount[a_id]["group_by_data"].keys()):
                total_amount_item2 = total_amount[a_id]["group_by_data"][key]
                if key not in trial_balance:
                    trial_balance[key] = {}
                    for f_name in f_names:
                        if f_name in total_amount_item2:
                            trial_balance[key][f_name] = 0
                    trial_balance[key]["account_data"] = {}
                for f_name in f_names:
                    if f_name in total_amount_item2:
                        trial_balance[key][f_name] += total_amount_item2[f_name]
                # Prepare data_item
                data_item = total_amount_item2
                data_item["type"] = "account_type"
                data_item["id"] = a_id
                data_item["name"] = accounts_data[a_id]["name"]
                data_item["code"] = accounts_data[a_id]["code"]
                if foreign_currency:
                    data_item["currency_id"] = accounts_data[a_id]["currency_id"]
                    data_item["currency_name"] = accounts_data[a_id]["currency_name"]
                trial_balance[key]["account_data"][a_id] = data_item
        analytic_account_ids = list(trial_balance.keys())
        aa_data = {}
        aaa_model = self.env["account.analytic.account"].with_context(active_test=False)
        analytic_accounts = aaa_model.search_read(
            domain=[("id", "in", analytic_account_ids)],
            fields=["display_name"],
        )
        for aa in analytic_accounts:
            aa_data[aa["id"]] = aa
        for aa_id in analytic_account_ids:
            trial_balance[aa_id]["id"] = aa_id
            trial_balance[aa_id]["type"] = "analytic_account_type"
            trial_balance[aa_id]["name"] = (
                aa_data[aa_id]["display_name"]
                if aa_id in aa_data
                else _("Without analytic account")
            )
            account_data_item = list(trial_balance[aa_id]["account_data"].values())
            account_data_item = sorted(account_data_item, key=lambda k: k["code"])
            trial_balance[aa_id]["account_data"] = account_data_item
            for f_name in f_names:
                if f_name in trial_balance[aa_id]:
                    total_amount_grouped[f_name] += trial_balance[aa_id][f_name]
        trial_balance = list(trial_balance.values())
        trial_balance = sorted(trial_balance, key=lambda k: k["name"])
        return trial_balance, total_amount_grouped

    def _get_hierarchy_groups(self, group_ids, groups_data, foreign_currency):
        processed_groups = []
        # Sort groups so that parent groups are processed before child groups
        groups = (
            self.env["account.group"]
            .browse(group_ids)
            .sorted(key=lambda x: x.complete_code)
        )
        for group in groups:
            group_id = group.id
            parent_id = groups_data[group_id]["parent_id"]
            if group_id in processed_groups:
                raise UserError(
                    _(
                        "There is a problem in the structure of the account groups. "
                        "You may need to create some child group of %s."
                    )
                    % groups_data[group_id]["name"]
                )
            else:
                processed_groups.append(parent_id)
            while parent_id:
                if parent_id not in groups_data.keys():
                    group = self.env["account.group"].browse(parent_id)
                    groups_data[group.id] = {
                        "id": group.id,
                        "code": group.code_prefix_start,
                        "name": group.name,
                        "parent_id": group.parent_id.id,
                        "complete_code": group.complete_code,
                        "account_ids": group.compute_account_ids.ids,
                        "type": "group_type",
                        "initial_balance": 0,
                        "debit": 0,
                        "credit": 0,
                        "balance": 0,
                        "ending_balance": 0,
                    }
                    if foreign_currency:
                        groups_data[group.id].update(
                            initial_currency_balance=0,
                            ending_currency_balance=0,
                        )
                acc_keys = ["debit", "credit", "balance"]
                acc_keys += ["initial_balance", "ending_balance"]
                for acc_key in acc_keys:
                    groups_data[parent_id][acc_key] += groups_data[group_id][acc_key]
                if foreign_currency:
                    groups_data[group_id]["initial_currency_balance"] += groups_data[
                        group_id
                    ]["initial_currency_balance"]
                    groups_data[group_id]["ending_currency_balance"] += groups_data[
                        group_id
                    ]["ending_currency_balance"]
                parent_id = groups_data[parent_id]["parent_id"]
        return groups_data

    def _get_groups_data(self, accounts_data, total_amount, foreign_currency):
        accounts_ids = list(accounts_data.keys())
        accounts = self.env["account.account"].browse(accounts_ids)
        account_group_relation = {}
        for account in accounts:
            accounts_data[account.id]["complete_code"] = (
                account.group_id.complete_code + " / " + account.code
                if account.group_id.id
                else ""
            )
            if account.group_id.id:
                if account.group_id.id not in account_group_relation.keys():
                    account_group_relation.update({account.group_id.id: [account.id]})
                else:
                    account_group_relation[account.group_id.id].append(account.id)
        groups = self.env["account.group"].browse(account_group_relation.keys())
        groups_data = {}
        for group in groups:
            groups_data.update(
                {
                    group.id: {
                        "id": group.id,
                        "code": group.code_prefix_start,
                        "name": group.name,
                        "parent_id": group.parent_id.id,
                        "type": "group_type",
                        "complete_code": group.complete_code,
                        "account_ids": group.compute_account_ids.ids,
                        "initial_balance": 0.0,
                        "credit": 0.0,
                        "debit": 0.0,
                        "balance": 0.0,
                        "ending_balance": 0.0,
                    }
                }
            )
            if foreign_currency:
                groups_data[group.id]["initial_currency_balance"] = 0.0
                groups_data[group.id]["ending_currency_balance"] = 0.0
        for group_id in account_group_relation.keys():
            for account_id in account_group_relation[group_id]:
                groups_data[group_id]["initial_balance"] += total_amount[account_id][
                    "initial_balance"
                ]
                groups_data[group_id]["debit"] += total_amount[account_id]["debit"]
                groups_data[group_id]["credit"] += total_amount[account_id]["credit"]
                groups_data[group_id]["balance"] += total_amount[account_id]["balance"]
                groups_data[group_id]["ending_balance"] += total_amount[account_id][
                    "ending_balance"
                ]
                if foreign_currency:
                    groups_data[group_id]["initial_currency_balance"] += total_amount[
                        account_id
                    ]["initial_currency_balance"]
                    groups_data[group_id]["ending_currency_balance"] += total_amount[
                        account_id
                    ]["ending_currency_balance"]
        group_ids = list(groups_data.keys())
        groups_data = self._get_hierarchy_groups(
            group_ids,
            groups_data,
            foreign_currency,
        )
        return groups_data

    def _get_computed_groups_data(self, accounts_data, total_amount, foreign_currency):
        groups = self.env["account.group"].search([("id", "!=", False)])
        groups_data = {}
        for group in groups:
            len_group_code = len(group.code_prefix_start)
            groups_data.update(
                {
                    group.id: {
                        "id": group.id,
                        "code": group.code_prefix_start,
                        "name": group.name,
                        "parent_id": group.parent_id.id,
                        "type": "group_type",
                        "complete_code": group.complete_code,
                        "account_ids": group.compute_account_ids.ids,
                        "initial_balance": 0.0,
                        "credit": 0.0,
                        "debit": 0.0,
                        "balance": 0.0,
                        "ending_balance": 0.0,
                    }
                }
            )
            if foreign_currency:
                groups_data[group.id]["initial_currency_balance"] = 0.0
                groups_data[group.id]["ending_currency_balance"] = 0.0
            for account in accounts_data.values():
                if group.code_prefix_start == account["code"][:len_group_code]:
                    acc_id = account["id"]
                    group_id = group.id
                    groups_data[group_id]["initial_balance"] += total_amount[acc_id][
                        "initial_balance"
                    ]
                    groups_data[group_id]["debit"] += total_amount[acc_id]["debit"]
                    groups_data[group_id]["credit"] += total_amount[acc_id]["credit"]
                    groups_data[group_id]["balance"] += total_amount[acc_id]["balance"]
                    groups_data[group_id]["ending_balance"] += total_amount[acc_id][
                        "ending_balance"
                    ]
                    if foreign_currency:
                        groups_data[group_id]["initial_currency_balance"] += (
                            total_amount[acc_id]["initial_currency_balance"]
                        )
                        groups_data[group_id]["ending_currency_balance"] += (
                            total_amount[acc_id]["ending_currency_balance"]
                        )
        return groups_data

    def _get_report_values(self, docids, data):
        show_partner_details = data["show_partner_details"]
        wizard_id = data["wizard_id"]
        company = self.env["res.company"].browse(data["company_id"])
        company_id = data["company_id"]
        partner_ids = data["partner_ids"]
        journal_ids = data["journal_ids"]
        account_ids = data["account_ids"]
        date_to = data["date_to"]
        date_from = data["date_from"]
        hide_account_at_0 = data["hide_account_at_0"]
        show_hierarchy = data["show_hierarchy"]
        show_hierarchy_level = data["show_hierarchy_level"]
        foreign_currency = data["foreign_currency"]
        only_posted_moves = data["only_posted_moves"]
        unaffected_earnings_account = data["unaffected_earnings_account"]
        fy_start_date = data["fy_start_date"]
        grouped_by = data["grouped_by"]
        total_amount, accounts_data, partners_data = self._get_data(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            date_to,
            date_from,
            foreign_currency,
            only_posted_moves,
            show_partner_details,
            hide_account_at_0,
            unaffected_earnings_account,
            fy_start_date,
            grouped_by,
        )
        trial_balance_grouped = False
        total_amount_grouped = False
        if grouped_by:
            trial_balance_grouped, total_amount_grouped = self._get_data_grouped(
                total_amount, accounts_data, foreign_currency
            )
        trial_balance = []
        if not show_partner_details:
            for account_id in accounts_data.keys():
                accounts_data[account_id].update(
                    {
                        "initial_balance": total_amount[account_id]["initial_balance"],
                        "credit": total_amount[account_id]["credit"],
                        "debit": total_amount[account_id]["debit"],
                        "balance": total_amount[account_id]["balance"],
                        "ending_balance": total_amount[account_id]["ending_balance"],
                        "group_by": (
                            total_amount[account_id]["group_by"]
                            if "group_by" in total_amount[account_id]
                            else False
                        ),
                        "group_by_data": (
                            total_amount[account_id]["group_by_data"]
                            if "group_by_data" in total_amount[account_id]
                            else False
                        ),
                        "type": "account_type",
                    }
                )
                if foreign_currency:
                    accounts_data[account_id].update(
                        {
                            "ending_currency_balance": total_amount[account_id][
                                "ending_currency_balance"
                            ],
                            "initial_currency_balance": total_amount[account_id][
                                "initial_currency_balance"
                            ],
                        }
                    )
            if show_hierarchy:
                groups_data = self._get_groups_data(
                    accounts_data, total_amount, foreign_currency
                )
                trial_balance = list(groups_data.values())
                trial_balance += list(accounts_data.values())
                trial_balance = sorted(trial_balance, key=lambda k: k["complete_code"])
                for trial in trial_balance:
                    counter = trial["complete_code"].count("/")
                    trial["level"] = counter
            else:
                trial_balance = list(accounts_data.values())
                trial_balance = sorted(trial_balance, key=lambda k: k["code"])
        else:
            if foreign_currency:
                for account_id in accounts_data.keys():
                    total_amount[account_id]["currency_id"] = accounts_data[account_id][
                        "currency_id"
                    ]
                    total_amount[account_id]["currency_name"] = accounts_data[
                        account_id
                    ]["currency_name"]
        return {
            "doc_ids": [wizard_id],
            "doc_model": "trial.balance.report.wizard",
            "docs": self.env["trial.balance.report.wizard"].browse(wizard_id),
            "foreign_currency": data["foreign_currency"],
            "company_name": company.display_name,
            "company_currency": company.currency_id,
            "currency_name": company.currency_id.name,
            "date_from": data["date_from"],
            "date_to": data["date_to"],
            "only_posted_moves": data["only_posted_moves"],
            "hide_account_at_0": data["hide_account_at_0"],
            "show_partner_details": data["show_partner_details"],
            "limit_hierarchy_level": data["limit_hierarchy_level"],
            "show_hierarchy": show_hierarchy,
            "hide_parent_hierarchy_level": data["hide_parent_hierarchy_level"],
            "trial_balance": trial_balance,
            "trial_balance_grouped": trial_balance_grouped,
            "total_amount": total_amount,
            "total_amount_grouped": total_amount_grouped,
            "accounts_data": accounts_data,
            "partners_data": partners_data,
            "show_hierarchy_level": show_hierarchy_level,
            "currency_model": self.env["res.currency"],
            "grouped_by": grouped_by,
        }
