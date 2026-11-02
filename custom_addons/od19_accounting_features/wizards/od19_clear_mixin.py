# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class Od19ClearWizardMixin(models.AbstractModel):
    """ตรรกะร่วมของ wizard กระทบยอดปิดงวดเฉพาะทาง (VAT / WHT / Suspense).

    ทุก wizard ที่สืบทอด mixin นี้จะได้ความสามารถพื้นฐานเหมือนกันคือ
    โหลดรายการค้าง (open item) ของบัญชีคุมงวดที่เลือกไว้ทั้งหมด
    (post แล้วแต่ยังไม่ reconcile และวันที่ <= ``date_to``) จัดกลุ่มตาม
    บัญชี+คู่ค้า แล้วล้างยอดด้วย helper กลาง
    ``account.move._od19_reconcile_move_lines``

    คลาสลูกกำหนดสิ่งที่ต้องทำเพิ่มผ่าน override point:
    * ``_od19_control_accounts`` (บังคับ) — บัญชีคุมที่ต้องล้างยอด
    * ``_od19_create_settlement_move`` (ทางเลือก) — สร้างรายการปิดงวด (settlement)
    """

    _name = "od19.clear.wizard.mixin"
    _description = "Clearing Wizard (Mixin)"

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Currency",
    )
    date_to = fields.Date(
        string="As of Date (ณ วันที่)",
        required=True,
        default=lambda self: fields.Date.context_today(self),
        help="ล้างยอดรายการค้างทั้งหมดที่มีวันทีต่ำกว่าหรือเท่ากับวันที่นี้",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Settlement Journal",
        required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self._od19_default_journal(),
    )

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model
    def _od19_default_journal(self):
        return self.env["account.journal"].search(
            [("type", "=", "general"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )

    # ------------------------------------------------------------------
    # Override points
    # ------------------------------------------------------------------
    def _od19_control_accounts(self):
        """Return the ``account.account`` recordset to clear (override)."""
        raise NotImplementedError

    def _od19_create_settlement_move(self):
        """Post the settlement journal entry (override when needed)."""
        return False

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    def _od19_open_line_domain(self):
        self.ensure_one()
        return [
            ("company_id", "=", self.company_id.id),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("date", "<=", self.date_to),
            ("account_id", "in", self._od19_control_accounts().ids),
        ]

    def _od19_open_lines_by_group(self):
        """Open items grouped by ``(account_id, partner_id)``."""
        self.ensure_one()
        account_move_line = self.env["account.move.line"]
        groups = {}
        for line in account_move_line.search(self._od19_open_line_domain()):
            key = (line.account_id.id, line.partner_id.id)
            groups.setdefault(key, account_move_line)
            groups[key] |= line
        return groups

    def _od19_account_open_balance(self, accounts):
        """Signed balance of the open lines of ``accounts`` as of ``date_to``."""
        self.ensure_one()
        if not accounts:
            return 0.0
        lines = self.env["account.move.line"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("account_id", "in", accounts.ids),
                ("parent_state", "=", "posted"),
                ("reconciled", "=", False),
                ("date", "<=", self.date_to),
            ]
        )
        return sum(lines.mapped("balance"))

    def _od19_post_settlement_move(self, line_commands, reference):
        """Create and post a balanced settlement entry."""
        self.ensure_one()
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": self.date_to,
                "journal_id": self.journal_id.id,
                "ref": reference,
                "line_ids": [(0, 0, vals) for vals in line_commands],
            }
        )
        move.action_post()
        return move

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_load(self):
        """(Re)load the open items grouped by account and partner."""
        self.ensure_one()
        self.line_ids.unlink()
        vals_list = [
            {
                "wizard_id": self.id,
                "account_id": account_id,
                "partner_id": partner_id,
                "line_count": len(group),
                "debit": sum(group.mapped("debit")),
                "credit": sum(group.mapped("credit")),
                "balance": sum(group.mapped("balance")),
            }
            for (account_id, partner_id), group in self._od19_open_lines_by_group().items()
        ]
        if vals_list:
            self.env[self._fields["line_ids"].comodel_name].create(vals_list)
        return self._od19_reload_action()

    def action_clear(self):
        """Post the settlement (when any) then reconcile every open group."""
        self.ensure_one()
        self._od19_create_settlement_move()
        reconcile = self.env["account.move"]._od19_reconcile_move_lines
        for group in self._od19_open_lines_by_group().values():
            reconcile(group)
        return self.action_load()

    def _od19_reload_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self._description,
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
