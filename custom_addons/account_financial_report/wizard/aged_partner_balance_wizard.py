# Author: Damien Crier, Andrea Stirpe, Kevin Graveman, Dennis Sluijk
# Author: Julien Coux
# Copyright 2016 Camptocamp SA, Onestein B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AgedPartnerBalanceWizard(models.TransientModel):
    """Aged partner balance report wizard."""

    _name = "aged.partner.balance.report.wizard"
    _description = "Aged Partner Balance Wizard"
    _inherit = "account_financial_report_abstract_wizard"

    date_at = fields.Date(required=True, default=fields.Date.context_today)
    date_from = fields.Date()
    target_move = fields.Selection(
        [("posted", "All Posted Entries"), ("all", "All Entries")],
        string="Target Moves",
        required=True,
        default="posted",
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        string="Filter accounts",
        domain=[("reconcile", "=", True)],
        required=True,
    )
    receivable_accounts_only = fields.Boolean()
    payable_accounts_only = fields.Boolean()
    partner_ids = fields.Many2many(comodel_name="res.partner", string="Filter partners")
    show_move_line_details = fields.Boolean()

    account_code_from = fields.Many2one(
        comodel_name="account.account",
        help="Starting account in a range",
    )
    account_code_to = fields.Many2one(
        comodel_name="account.account",
        help="Ending account in a range",
    )
    age_partner_config_id = fields.Many2one(
        "account.age.report.configuration", string="Intervals configuration"
    )

    @api.onchange("account_code_from", "account_code_to")
    def on_change_account_range(self):
        if (
            self.account_code_from
            and self.account_code_from.code.isdigit()
            and self.account_code_to
            and self.account_code_to.code.isdigit()
        ):
            start_range = int(self.account_code_from.code)
            end_range = int(self.account_code_to.code)
            self.account_ids = self.env["account.account"].search(
                [
                    ("code", ">=", start_range),
                    ("code", "<=", end_range),
                    ("reconcile", "=", True),
                ]
            )
            if self.company_id:
                self.account_ids = self.account_ids.filtered(
                    lambda a: self.company_id in a.company_ids
                )
        return {
            "domain": {
                "account_code_from": [("reconcile", "=", True)],
                "account_code_to": [("reconcile", "=", True)],
            }
        }

    @api.onchange("company_id")
    def onchange_company_id(self):
        """Handle company change."""
        if self.company_id and self.partner_ids:
            self.partner_ids = self.partner_ids.filtered(
                lambda p: p.company_id == self.company_id or not p.company_id
            )
        if self.company_id and self.account_ids:
            if self.receivable_accounts_only or self.payable_accounts_only:
                self.onchange_type_accounts_only()
            else:
                self.account_ids = self.account_ids.filtered(
                    lambda a: self.company_id in a.company_ids
                )
        res = {"domain": {"account_ids": [], "partner_ids": []}}
        if not self.company_id:
            return res
        else:
            res["domain"]["account_ids"] += [
                ("company_ids", "in", [self.company_id.id])
            ]
            res["domain"]["partner_ids"] += self._get_partner_ids_domain()
        return res

    @api.onchange("account_ids")
    def onchange_account_ids(self):
        return {"domain": {"account_ids": [("reconcile", "=", True)]}}

    @api.onchange("receivable_accounts_only", "payable_accounts_only")
    def onchange_type_accounts_only(self):
        """Handle receivable/payable accounts only change."""
        domain = [("company_ids", "in", [self.company_id.id])]
        if self.receivable_accounts_only or self.payable_accounts_only:
            if self.receivable_accounts_only and self.payable_accounts_only:
                domain += [
                    ("account_type", "in", ("asset_receivable", "liability_payable"))
                ]
            elif self.receivable_accounts_only:
                domain += [("account_type", "=", "asset_receivable")]
            elif self.payable_accounts_only:
                domain += [("account_type", "=", "liability_payable")]
            self.account_ids = self.env["account.account"].search(domain)
        else:
            self.account_ids = None

    def _print_report(self, report_type):
        self.ensure_one()
        data = self._prepare_report_aged_partner_balance()
        if report_type == "xlsx":
            report_name = "a_f_r.report_aged_partner_balance_xlsx"
        else:
            report_name = "account_financial_report.aged_partner_balance"
        return (
            self.env["ir.actions.report"]
            .search(
                [("report_name", "=", report_name), ("report_type", "=", report_type)],
                limit=1,
            )
            .report_action(self, data=data)
        )

    def _prepare_report_aged_partner_balance(self):
        self.ensure_one()
        return {
            "wizard_id": self.id,
            "date_at": self.date_at,
            "date_from": self.date_from or False,
            "only_posted_moves": self.target_move == "posted",
            "company_id": self.company_id.id,
            "account_ids": self.account_ids.ids,
            "partner_ids": self.partner_ids.ids,
            "show_move_line_details": self.show_move_line_details,
            "account_financial_report_lang": self.env.lang,
            "age_partner_config_id": self.age_partner_config_id.id,
        }

    def _export(self, report_type):
        """Default export is PDF."""
        return self._print_report(report_type)
