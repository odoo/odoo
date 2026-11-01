# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class Od19AccountWhtClearLine(models.TransientModel):
    _name = "od19.account.wht.clear.line"
    _description = "WHT Clearing Open Item"

    wizard_id = fields.Many2one(
        comodel_name="od19.account.wht.clear.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    account_id = fields.Many2one(
        comodel_name="account.account", string="Account", readonly=True
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Partner", readonly=True
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="wizard_id.currency_id",
        string="Currency",
    )
    line_count = fields.Integer(string="Open Items", readonly=True)
    debit = fields.Monetary(string="Debit", currency_field="currency_id", readonly=True)
    credit = fields.Monetary(
        string="Credit", currency_field="currency_id", readonly=True
    )
    balance = fields.Monetary(
        string="Balance", currency_field="currency_id", readonly=True
    )


class Od19AccountWhtClearWizard(models.TransientModel):
    """WHT Clearing (ล้างบัญชีภาษีหัก ณ ที่จ่าย).

    รวมยอดภาษีหัก ณ ที่จ่ายค้างจ่าย (แยกตามอัตรา 1% / 3% / 5%) ของงวด
    โอนยอดสุทธิไปยังบัญชีภาษีหัก ณ ที่จ่ายนำส่งกรมสรรพากร (ภ.ง.ด.3 / ภ.ง.ด.53)
    แล้วกระทบยอดรายการค้างทั้งหมดในบัญชีคุมให้เป็นศูนย์
    """

    _name = "od19.account.wht.clear.wizard"
    _inherit = ["od19.clear.wizard.mixin"]
    _description = "WHT Clearing (ภาษีหัก ณ ที่จ่าย)"

    wht_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="od19_wht_clear_account_rel",
        column1="wizard_id",
        column2="account_id",
        string="WHT Payable (ภาษีหัก ณ ที่จ่ายค้างจ่าย)",
        domain="[('reconcile', '=', True), ('company_ids', 'in', company_id)]",
        default=lambda self: self.env.company.od19_wht_payable_account_ids.ids,
    )
    settlement_account_id = fields.Many2one(
        comodel_name="account.account",
        string="WHT to Remit (ภาษีหัก ณ ที่จ่ายนำส่ง)",
        domain="[('account_type', 'in', ('liability_current', 'liability_payable')),"
        " ('company_ids', 'in', company_id)]",
        default=lambda self: self.env.company.od19_wht_settlement_account_id.id,
    )
    od19_post_settlement = fields.Boolean(
        string="Create Settlement Entry",
        default=True,
        help="เปิดเพื่อตั้งรายการปิดงวดโอนยอดภาษีหัก ณ ที่จ่ายไปบัญชีนำส่ง "
        "ปิดเพื่อกระทบยอด (reconcile) เท่านั้น",
    )
    wht_balance = fields.Monetary(
        string="WHT Payable Balance",
        currency_field="currency_id",
        compute="_compute_wht_balance",
    )
    line_ids = fields.One2many(
        comodel_name="od19.account.wht.clear.line",
        inverse_name="wizard_id",
        string="Open Items",
        readonly=True,
    )

    @api.depends("wht_account_ids", "date_to", "company_id")
    def _compute_wht_balance(self):
        for wizard in self:
            wizard.wht_balance = -wizard._od19_account_open_balance(
                wizard.wht_account_ids
            )

    def _od19_control_accounts(self):
        self.ensure_one()
        return self.wht_account_ids

    def _od19_create_settlement_move(self):
        """Consolidate the WHT payable balances into the remit account."""
        self.ensure_one()
        if not self.od19_post_settlement:
            return False
        reference = self.env._("WHT Clearing (ภาษีหัก ณ ที่จ่าย)")
        line_commands = []
        total = 0.0
        for account in self.wht_account_ids:
            amount = -self._od19_account_open_balance(account)
            if self.currency_id.is_zero(amount):
                continue
            total += amount
            line_commands.append(
                {
                    "name": reference,
                    "account_id": account.id,
                    "debit": amount,
                    "credit": 0.0,
                }
            )
        if not line_commands:
            return False
        if not self.settlement_account_id:
            raise UserError(
                self.env._(
                    "กรุณาเลือกบัญชีภาษีหัก ณ ที่จ่ายนำส่ง (WHT to Remit) "
                    "ก่อนล้างยอด"
                )
            )
        line_commands.append(
            {
                "name": reference,
                "account_id": self.settlement_account_id.id,
                "debit": 0.0,
                "credit": total,
            }
        )
        return self._od19_post_settlement_move(line_commands, reference)
