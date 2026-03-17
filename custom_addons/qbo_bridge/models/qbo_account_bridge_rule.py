from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

ACCOUNT_TYPE_SELECTION = [
    ("asset_receivable", "Receivable"),
    ("asset_cash", "Bank and Cash"),
    ("asset_current", "Current Assets"),
    ("asset_non_current", "Non-current Assets"),
    ("asset_prepayments", "Prepayments"),
    ("asset_fixed", "Fixed Assets"),
    ("liability_payable", "Payable"),
    ("liability_credit_card", "Credit Card"),
    ("liability_current", "Current Liabilities"),
    ("liability_non_current", "Non-current Liabilities"),
    ("equity", "Equity"),
    ("equity_unaffected", "Current Year Earnings"),
    ("income", "Income"),
    ("income_other", "Other Income"),
    ("expense", "Expenses"),
    ("expense_other", "Other Expenses"),
    ("expense_depreciation", "Depreciation"),
    ("expense_direct_cost", "Cost of Revenue"),
    ("off_balance", "Off-Balance Sheet"),
]


class QboAccountBridgeRule(models.Model):
    _name = "qbo.account.bridge.rule"
    _description = "QBO canonical account bridge rule"
    _order = "sequence, canonical_code, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    name = fields.Char(
        compute="_compute_name",
        store=True,
    )

    match_acct_num = fields.Char(string="Match QBO account number")
    match_name = fields.Char(string="Match QBO account name")
    match_account_type = fields.Char(string="Match QBO account type")
    match_account_subtype = fields.Char(string="Match QBO detail type")

    canonical_code = fields.Char(string="Canonical code", required=True)
    canonical_name = fields.Char(string="Canonical name", required=True)
    canonical_account_type = fields.Selection(
        ACCOUNT_TYPE_SELECTION,
        string="Canonical account type",
        required=True,
    )
    notes = fields.Text()
    linked_account_count = fields.Integer(
        compute="_compute_linked_account_count",
        string="Linked accounts",
    )

    @api.depends("canonical_code", "canonical_name")
    def _compute_name(self):
        for rec in self:
            parts = [part for part in [rec.canonical_code, rec.canonical_name] if part]
            rec.name = " - ".join(parts)

    def _compute_linked_account_count(self):
        grouped = self.env["account.account"].read_group(
            [("qbo_bridge_rule_id", "in", self.ids)],
            ["qbo_bridge_rule_id"],
            ["qbo_bridge_rule_id"],
        )
        count_by_rule = {
            item["qbo_bridge_rule_id"][0]: item["qbo_bridge_rule_id_count"]
            for item in grouped
            if item.get("qbo_bridge_rule_id")
        }
        for rec in self:
            rec.linked_account_count = count_by_rule.get(rec.id, 0)

    @api.constrains(
        "match_acct_num",
        "match_name",
        "match_account_type",
        "match_account_subtype",
    )
    def _check_match_fields(self):
        for rec in self:
            if not any(
                [
                    rec.match_acct_num,
                    rec.match_name,
                    rec.match_account_type,
                    rec.match_account_subtype,
                ],
            ):
                raise ValidationError(
                    _("Add at least one QBO match field to the bridge rule."),
                )

    @api.model
    def match_qbo_record(self, record):
        for rule in self.search([("active", "=", True)]):
            if rule._matches_record(record):
                return rule
        return self.browse()

    def _matches_record(self, record):
        self.ensure_one()
        comparators = {
            "match_acct_num": record.get("AcctNum"),
            "match_name": record.get("Name"),
            "match_account_type": record.get("AccountType"),
            "match_account_subtype": record.get("AccountSubType"),
        }
        for field_name, value in comparators.items():
            rule_value = getattr(self, field_name)
            if rule_value and self._normalize(rule_value) != self._normalize(value):
                return False
        return True

    @api.model
    def _normalize(self, value):
        return (value or "").strip().casefold()

    def action_view_linked_accounts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Accounts using %s") % self.display_name,
            "res_model": "account.account",
            "view_mode": "list,form",
            "domain": [("qbo_bridge_rule_id", "=", self.id)],
            "context": {"search_default_current_company": 1},
        }
