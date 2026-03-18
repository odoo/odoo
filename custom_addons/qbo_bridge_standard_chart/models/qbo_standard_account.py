import csv
import io
from pathlib import Path

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.modules.module import get_module_path

NORMAL_BALANCE_SELECTION = [
    ("debit", "Debit"),
    ("credit", "Credit"),
]

ENTRY_TYPE_SELECTION = [
    ("header", "Header"),
    ("detail", "Detail"),
]


class QboStandardAccount(models.Model):
    _name = "qbo.standard.account"
    _description = "QBO standard chart account"
    _order = "code, entry_type, id"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name", store=True)
    active = fields.Boolean(default=True)
    code = fields.Char(required=True, index=True)
    description = fields.Char(required=True)
    long_description = fields.Text()
    entry_type = fields.Selection(ENTRY_TYPE_SELECTION, required=True, index=True)
    category = fields.Char(required=True, index=True)
    fs_mapping = fields.Char(string="Financial statement mapping")
    parent_code = fields.Char(index=True)
    parent_id = fields.Many2one(
        "qbo.standard.account",
        string="Parent standard account",
        ondelete="set null",
    )
    child_ids = fields.One2many("qbo.standard.account", "parent_id", string="Child accounts")
    normal_balance = fields.Selection(NORMAL_BALANCE_SELECTION, required=True)
    tags = fields.Text()
    default_vendors = fields.Text()
    regulatory_mapping = fields.Text()
    start_date = fields.Date()
    end_date = fields.Date()
    notes = fields.Text()
    subcategory = fields.Char()
    cash_flow_classification = fields.Char()
    cost_center = fields.Char()
    gaap_classification = fields.Char(string="GAAP classification")
    detailed_description = fields.Text()
    odoo_account_type = fields.Selection(
        selection=lambda self: self.env["account.account"]._fields["account_type"].selection,
        string="Odoo account type",
        required=True,
    )
    bridge_rule_ids = fields.One2many(
        "qbo.account.bridge.rule",
        "standard_account_id",
        string="Bridge rules",
    )
    bridge_rule_count = fields.Integer(compute="_compute_bridge_rule_count")
    linked_account_ids = fields.One2many(
        "account.account",
        "qbo_standard_account_id",
        string="Company accounts",
    )
    linked_account_count = fields.Integer(compute="_compute_linked_account_count")

    _sql_constraints = [
        (
            "qbo_standard_account_code_type_uniq",
            "UNIQUE(code, entry_type)",
            "Each standard chart code can appear only once per entry type.",
        ),
    ]

    @api.depends("code", "description", "entry_type")
    def _compute_name(self):
        for rec in self:
            label = rec.description or ""
            suffix = "Header" if rec.entry_type == "header" else "Detail"
            rec.name = f"[{rec.code}] {label} ({suffix})"

    def _compute_bridge_rule_count(self):
        grouped = self.env["qbo.account.bridge.rule"].read_group(
            [("standard_account_id", "in", self.ids)],
            ["standard_account_id"],
            ["standard_account_id"],
        )
        counts = {
            item["standard_account_id"][0]: item["standard_account_id_count"]
            for item in grouped
            if item.get("standard_account_id")
        }
        for rec in self:
            rec.bridge_rule_count = counts.get(rec.id, 0)

    def _compute_linked_account_count(self):
        grouped = self.env["account.account"].read_group(
            [("qbo_standard_account_id", "in", self.ids)],
            ["qbo_standard_account_id"],
            ["qbo_standard_account_id"],
        )
        counts = {
            item["qbo_standard_account_id"][0]: item["qbo_standard_account_id_count"]
            for item in grouped
            if item.get("qbo_standard_account_id")
        }
        for rec in self:
            rec.linked_account_count = counts.get(rec.id, 0)

    @api.model
    def import_chart_rows(self, rows):
        stats = {"created": 0, "updated": 0, "parents_linked": 0}
        existing = {
            (rec.code, rec.entry_type): rec
            for rec in self.search([])
        }
        for row in rows:
            vals = self._prepare_vals_from_csv_row(row)
            key = (vals["code"], vals["entry_type"])
            record = existing.get(key)
            if record:
                record.write(vals)
                stats["updated"] += 1
            else:
                record = self.create(vals)
                existing[key] = record
                stats["created"] += 1

        stats["parents_linked"] = self._resolve_parent_links()
        return stats

    @api.model
    def import_chart_from_bytes(self, csv_bytes):
        text = csv_bytes.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
        if not rows:
            raise UserError(_("The uploaded CSV did not contain any rows."))
        return self.import_chart_rows(rows)

    @api.model
    def import_bundled_chart(self):
        module_path = get_module_path("qbo_bridge_standard_chart")
        csv_path = (
            Path(module_path) / "data" / "standard_chart_seed.csv"
            if module_path
            else None
        )
        if not csv_path:
            raise UserError(_("Could not locate the bundled standard chart seed file."))
        csv_bytes = Path(csv_path).read_bytes()
        return self.import_chart_from_bytes(csv_bytes)

    @api.model
    def _prepare_vals_from_csv_row(self, row):
        entry_type = (row.get("type") or "detail").strip().lower()
        normal_balance = (row.get("normal_balance") or "debit").strip().lower()
        return {
            "active": not bool((row.get("end_date") or "").strip()),
            "code": (row.get("code") or "").strip(),
            "description": (row.get("description") or "").strip(),
            "long_description": row.get("long_description") or False,
            "entry_type": entry_type,
            "category": (row.get("category") or "").strip(),
            "fs_mapping": (row.get("fs_mapping") or "").strip(),
            "parent_code": (row.get("parent_code") or "").strip() or False,
            "normal_balance": normal_balance,
            "tags": row.get("tags") or False,
            "default_vendors": row.get("default_vendors") or False,
            "regulatory_mapping": row.get("regulatory_mapping") or False,
            "start_date": (row.get("start_date") or "").strip() or False,
            "end_date": (row.get("end_date") or "").strip() or False,
            "notes": row.get("notes") or False,
            "subcategory": (row.get("subcategory") or "").strip() or False,
            "cash_flow_classification": (
                (row.get("cash_flow_classification") or "").strip() or False
            ),
            "cost_center": (row.get("cost_center") or "").strip() or False,
            "gaap_classification": (row.get("GAAP_classification") or "").strip() or False,
            "detailed_description": row.get("detailed_description") or False,
            "odoo_account_type": self._guess_odoo_account_type(row),
        }

    @api.model
    def _resolve_parent_links(self):
        headers = {
            rec.code: rec
            for rec in self.search([("entry_type", "=", "header")])
        }
        updates = 0
        for rec in self.search([("parent_code", "!=", False)]):
            parent = headers.get(rec.parent_code)
            parent_id = parent.id if parent else False
            if rec.parent_id.id != parent_id:
                rec.parent_id = parent_id
                updates += 1
        return updates

    @api.model
    def _guess_odoo_account_type(self, row):
        category = (row.get("category") or "").strip().lower()
        subcategory = (row.get("subcategory") or "").strip().lower()
        description = (row.get("description") or "").strip().lower()
        normal_balance = (row.get("normal_balance") or "").strip().lower()
        signature = " ".join(filter(None, [subcategory, description]))

        if category == "asset":
            if "receivable" in signature:
                return "asset_receivable"
            if any(token in signature for token in ["cash", "bank", "deposit"]):
                return "asset_cash"
            if "prepaid" in signature:
                return "asset_prepayments"
            if any(token in signature for token in ["fixed", "property", "equipment"]):
                return "asset_fixed"
            if any(token in signature for token in ["long-term", "non-current", "investment"]):
                return "asset_non_current"
            return "asset_current"

        if category == "liability":
            if "payable" in signature:
                return "liability_payable"
            if "credit card" in signature:
                return "liability_credit_card"
            if any(token in signature for token in ["long-term", "non-current", "loan", "debt"]):
                return "liability_non_current"
            return "liability_current"

        if category == "equity":
            return "equity"

        if category == "revenue":
            return "income"

        if category == "cost of goods sold":
            return "expense_direct_cost"

        if category == "expense":
            if any(token in signature for token in ["depreciation", "amortization"]):
                return "expense_depreciation"
            return "expense"

        if category == "other":
            return "income_other" if normal_balance == "credit" else "expense_other"

        return "off_balance"

    def action_view_bridge_rules(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Bridge Rules - %s") % self.display_name,
            "res_model": "qbo.account.bridge.rule",
            "view_mode": "list,form",
            "domain": [("standard_account_id", "=", self.id)],
        }

    def action_view_linked_accounts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Company Accounts - %s") % self.display_name,
            "res_model": "account.account",
            "view_mode": "list,form",
            "domain": [("qbo_standard_account_id", "=", self.id)],
        }

    def action_open_sync_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sync Standard Account"),
            "res_model": "qbo.standard.account.sync.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_standard_account_id": self.id},
        }

    def action_open_import_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Import Standard Chart"),
            "res_model": "qbo.standard.chart.import.wizard",
            "view_mode": "form",
            "target": "new",
        }

    def prepare_company_account_vals(self, company):
        self.ensure_one()
        note = self.long_description or self.detailed_description or self.notes
        return {
            "name": self.description,
            "code": self.code,
            "account_type": self.odoo_account_type,
            "description": self.detailed_description or self.long_description or False,
            "note": note,
            "active": self.active,
            "company_ids": [(4, company.id)],
            "qbo_standard_account_id": self.id,
        }

    @api.model
    def sync_detail_accounts_to_company(self, company, update_existing=True):
        account_model = self.env["account.account"].with_company(company)
        stats = {"created": 0, "updated": 0, "skipped": 0}
        detail_accounts = self.search([("entry_type", "=", "detail")], order="code")
        for standard_account in detail_accounts:
            account = account_model.search(
                [
                    ("company_ids", "=", company.id),
                    ("qbo_standard_account_id", "=", standard_account.id),
                ],
                limit=1,
            )
            if not account:
                account = account_model.search(
                    [
                        ("company_ids", "=", company.id),
                        ("code", "=", standard_account.code),
                    ],
                    limit=1,
                )

            vals = standard_account.prepare_company_account_vals(company)
            if account:
                if not update_existing:
                    stats["skipped"] += 1
                    continue
                account.write(vals)
                stats["updated"] += 1
            else:
                account_model.create(vals)
                stats["created"] += 1

        return stats
