from datetime import date

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

from odoo.addons.account.tools.display_types import NON_ACCOUNTABLE_DISPLAY_TYPES

_debug = DebugLog(__name__)


class AccountAutoReconcileWizard(models.TransientModel):
    _name = "account.auto.reconcile.wizard"
    _description = "Account automatic reconciliation wizard"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        readonly=True,
        required=True,
    )
    line_ids = fields.Many2many(comodel_name="account.move.line")
    from_date = fields.Date(string="From")
    to_date = fields.Date(
        string="To",
        default=fields.Date.context_today,
        required=True,
    )
    account_ids = fields.Many2many(
        comodel_name="account.account",
        string="Accounts",
        domain="[('reconcile', '=', True), ('account_type', '!=', 'off_balance')]",
        check_company=True,
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Partners",
        domain="[('company_id', 'in', [False, company_id]), '|', ('parent_id', '=', False), ('is_company', '=', True)]",
        check_company=True,
    )
    search_mode = fields.Selection(
        selection=[
            ("one_to_one", "Perfect Match"),
            ("zero_balance", "Clear Account"),
        ],
        string="Reconcile",
        default="one_to_one",
        required=True,
        help="Reconcile journal items with opposite balance or clear accounts with a zero balance",
    )

    @api.model
    @_debug.perf.timed
    def default_get(self, fields):
        _debug.lifecycle("default_get", records=self)
        res = super().default_get(fields)
        domain = self.env.context.get("domain")
        if "line_ids" in fields and "line_ids" not in res and domain:
            amls = self.env["account.move.line"].search(domain)
            if amls:
                res.update(self._prepare_default_wizard_values(amls))
                res["line_ids"] = [Command.set(amls.ids)]
        return res

    @api.model
    def _prepare_default_wizard_values(self, amls):
        return {
            "account_ids": [Command.set(amls[0].account_id.ids)]
            if all(aml.account_id == amls[0].account_id for aml in amls)
            else [],
            "partner_ids": [Command.set(amls[0].partner_id.ids)]
            if all(aml.partner_id == amls[0].partner_id for aml in amls)
            else [],
            "search_mode": "zero_balance"
            if amls.company_currency_id.is_zero(sum(amls.mapped("balance")))
            else "one_to_one",
            "from_date": min(amls.mapped("date")),
            "to_date": max(amls.mapped("date")),
        }

    def _prepare_wizard_values(self):
        self.check_singleton()
        return {
            "account_ids": [Command.set(self.account_ids.ids)]
            if self.account_ids
            else [],
            "partner_ids": [Command.set(self.partner_ids.ids)]
            if self.partner_ids
            else [],
            "search_mode": self.search_mode,
            "from_date": self.from_date,
            "to_date": self.to_date,
        }

    def _get_domain_amls(self):
        self.check_singleton()
        if (
            self.line_ids
            and self._prepare_wizard_values()
            == self._prepare_default_wizard_values(self.line_ids)
        ):
            _debug.logic(
                "amls_domain_chosen", autoreconcile=self, mode="selected_lines"
            )
            domain = [("id", "in", self.line_ids.ids)]
        else:
            domain = [
                ("company_id", "=", self.company_id.id),
                ("parent_state", "=", "posted"),
                ("display_type", "not in", NON_ACCOUNTABLE_DISPLAY_TYPES),
                ("date", ">=", self.from_date or date.min),
                ("date", "<=", self.to_date),
                ("reconciled", "=", False),
                ("account_id.reconcile", "=", True),
                ("amount_residual_currency", "!=", 0.0),
                ("amount_residual", "!=", 0.0),
            ]
            if self.account_ids:
                domain.append(("account_id", "in", self.account_ids.ids))
            if self.partner_ids:
                domain.append(("partner_id", "in", self.partner_ids.ids))
            _debug.logic(
                "amls_domain_chosen",
                autoreconcile=self,
                mode="filters",
                accounts=self.account_ids,
                partners=self.partner_ids,
            )
        return domain

    def _auto_reconcile_one_to_one(self):
        grouped_amls_data = self.env["account.move.line"]._read_group(
            self._get_domain_amls(),
            [
                "account_id",
                "partner_id",
                "currency_id",
                "amount_residual_currency:abs_rounded",
            ],
            ["id:recordset"],
        )
        all_reconciled_amls = self.env["account.move.line"]
        amls_grouped_by_2 = []
        for *__, grouped_aml_ids in grouped_amls_data:
            positive_amls = grouped_aml_ids.filtered(
                lambda aml: aml.amount_residual_currency >= 0
            ).sorted("date")
            negative_amls = (grouped_aml_ids - positive_amls).sorted("date")
            min_len = min(len(positive_amls), len(negative_amls))
            positive_amls = positive_amls[:min_len]
            negative_amls = negative_amls[:min_len]
            all_reconciled_amls += positive_amls + negative_amls
            amls_grouped_by_2 += [
                pos_aml + neg_aml
                for (pos_aml, neg_aml) in zip(positive_amls, negative_amls, strict=True)
            ]
        _debug.pipeline(
            "one_to_one",
            autoreconcile=self,
            grouped_amls_data_count=len(grouped_amls_data),
            amls_grouped_by_2_count=len(amls_grouped_by_2),
        )
        self.env["account.move.line"]._reconcile_plan(amls_grouped_by_2)
        return all_reconciled_amls

    def _auto_reconcile_zero_balance(self):
        grouped_amls_data = self.env["account.move.line"]._read_group(
            self._get_domain_amls(),
            groupby=["account_id", "partner_id", "currency_id"],
            aggregates=["id:recordset"],
            having=[("amount_residual_currency:sum_rounded", "=", 0)],
        )
        all_reconciled_amls = self.env["account.move.line"]
        amls_grouped_together = []
        for aml_data in grouped_amls_data:
            all_reconciled_amls += aml_data[-1]
            amls_grouped_together += [aml_data[-1]]
        _debug.pipeline(
            "zero_balance",
            autoreconcile=self,
            amls_grouped_together_count=len(amls_grouped_together),
            all_reconciled_amls_count=len(all_reconciled_amls),
        )
        self.env["account.move.line"]._reconcile_plan(amls_grouped_together)
        return all_reconciled_amls

    def auto_reconcile(self):
        self.check_singleton()
        if self.search_mode == "zero_balance":
            reconciled_amls = self._auto_reconcile_zero_balance()
        else:
            reconciled_amls = self._auto_reconcile_one_to_one()
        reconciled_amls_and_related = self.env["account.move.line"].search(
            [("full_reconcile_id", "in", reconciled_amls.full_reconcile_id.ids)]
        )
        _debug.pipeline(
            "auto_reconcile_done",
            autoreconcile=self,
            search_mode=self.search_mode,
            reconciled=reconciled_amls,
            related=reconciled_amls_and_related,
        )
        if reconciled_amls_and_related:
            return {
                "name": _("Automatically Reconciled Entries"),
                "type": "ir.actions.act_window",
                "res_model": "account.move.line",
                "context": "{'search_default_group_by_matching': True}",
                "view_mode": "list",
                "domain": [("id", "in", reconciled_amls_and_related.ids)],
            }
        else:
            raise UserError(self.env._("Nothing to reconcile."))
