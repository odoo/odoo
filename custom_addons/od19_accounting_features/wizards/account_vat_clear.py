# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class Od19AccountVatClearLine(models.TransientModel):
    _name = "od19.account.vat.clear.line"
    _description = "VAT Clearing Open Item"

    wizard_id = fields.Many2one(
        comodel_name="od19.account.vat.clear.wizard",
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


class Od19AccountVatClearWizard(models.TransientModel):
    """VAT Clearing (ล้างบัญชีภาษีมูลค่าเพิ่ม ภ.พ.30).

    รวมยอดภาษีขาย (output VAT) หักด้วยภาษีซื้อ (input VAT) ของงวด แล้วตั้ง
    รายการปิดงวด (settlement) เพื่อล้างบัญชีคุมทั้งสองให้เป็นศูนย์ พร้อมโอน
    ยอดสุทธิไปยังบัญชีภาษีมูลค่าเพิ่มค้างจ่าย (หรือรอขอคืน) จากนั้นกระทบยอด
    (reconcile) รายการค้างทั้งหมดในบัญชีคุมด้วย helper กลาง
    """

    _name = "od19.account.vat.clear.wizard"
    _inherit = ["od19.clear.wizard.mixin"]
    _description = "VAT Clearing (ภ.พ.30)"

    output_vat_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="od19_vat_clear_output_rel",
        column1="wizard_id",
        column2="account_id",
        string="Output VAT (ภาษีขาย)",
        domain="[('reconcile', '=', True), ('company_ids', 'in', company_id)]",
        default=lambda self: self.env.company.od19_vat_output_account_id.ids,
    )
    input_vat_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="od19_vat_clear_input_rel",
        column1="wizard_id",
        column2="account_id",
        string="Input VAT (ภาษีซื้อ)",
        domain="[('reconcile', '=', True), ('company_ids', 'in', company_id)]",
        default=lambda self: self.env.company.od19_vat_input_account_id.ids,
    )
    settlement_account_id = fields.Many2one(
        comodel_name="account.account",
        string="VAT Payable (ภาษีมูลค่าเพิ่มค้างจ่าย)",
        domain="[('account_type', 'in', ('liability_current', 'liability_payable')),"
        " ('company_ids', 'in', company_id)]",
        default=lambda self: self.env.company.od19_vat_settlement_account_id.id,
    )
    refund_account_id = fields.Many2one(
        comodel_name="account.account",
        string="VAT Refundable (ภาษีมูลค่าเพิ่มรอขอคืน)",
        domain="[('account_type', 'in', ('asset_current', 'asset_receivable')),"
        " ('company_ids', 'in', company_id)]",
        default=lambda self: self.env.company.od19_vat_refund_account_id.id,
    )
    output_vat_balance = fields.Monetary(
        string="Output VAT Balance",
        currency_field="currency_id",
        compute="_compute_vat_balances",
    )
    input_vat_balance = fields.Monetary(
        string="Input VAT Balance",
        currency_field="currency_id",
        compute="_compute_vat_balances",
    )
    net_vat_amount = fields.Monetary(
        string="Net VAT",
        currency_field="currency_id",
        compute="_compute_vat_balances",
    )
    net_vat_type = fields.Selection(
        selection=[
            ("payable", "Payable / ค้างจ่าย"),
            ("refundable", "Refundable / รอขอคืน"),
            ("zero", "Zero / สุทธิเป็นศูนย์"),
        ],
        string="Net VAT Type",
        compute="_compute_vat_balances",
    )
    line_ids = fields.One2many(
        comodel_name="od19.account.vat.clear.line",
        inverse_name="wizard_id",
        string="Open Items",
        readonly=True,
    )

    @api.depends(
        "output_vat_account_ids",
        "input_vat_account_ids",
        "date_to",
        "company_id",
    )
    def _compute_vat_balances(self):
        for wizard in self:
            output_balance = -wizard._od19_account_open_balance(
                wizard.output_vat_account_ids
            )
            input_balance = wizard._od19_account_open_balance(
                wizard.input_vat_account_ids
            )
            wizard.output_vat_balance = output_balance
            wizard.input_vat_balance = input_balance
            net = output_balance - input_balance
            wizard.net_vat_amount = net
            if not self.env.company.currency_id.is_zero(net):
                wizard.net_vat_type = "payable" if net > 0 else "refundable"
            else:
                wizard.net_vat_type = "zero"

    def _od19_control_accounts(self):
        self.ensure_one()
        return self.output_vat_account_ids | self.input_vat_account_ids

    def _od19_create_settlement_move(self):
        """Clear output/input VAT and transfer the net to payable/refundable."""
        self.ensure_one()
        reference = self.env._("VAT Clearing (ภ.พ.30)")
        line_commands = []
        for account in self.output_vat_account_ids:
            amount = -self._od19_account_open_balance(account)
            if self.currency_id.is_zero(amount):
                continue
            line_commands.append(
                {
                    "name": reference,
                    "account_id": account.id,
                    "debit": amount,
                    "credit": 0.0,
                }
            )
        for account in self.input_vat_account_ids:
            amount = self._od19_account_open_balance(account)
            if self.currency_id.is_zero(amount):
                continue
            line_commands.append(
                {
                    "name": reference,
                    "account_id": account.id,
                    "debit": 0.0,
                    "credit": amount,
                }
            )
        net = self.output_vat_balance - self.input_vat_balance
        if self.currency_id.is_zero(net):
            return self._od19_post_settlement_move(line_commands, reference) if line_commands else False
        if net > 0:
            if not self.settlement_account_id:
                raise UserError(
                    self.env._(
                        "กรุณาเลือกบัญชีภาษีมูลค่าเพิ่มค้างจ่าย (VAT Payable) "
                        "ก่อนล้างยอด"
                    )
                )
            line_commands.append(
                {
                    "name": reference,
                    "account_id": self.settlement_account_id.id,
                    "debit": 0.0,
                    "credit": net,
                }
            )
        else:
            if not self.refund_account_id:
                raise UserError(
                    self.env._(
                        "ภาษีซื้อมากกว่าภาษีขาย กรุณาเลือกบัญชีภาษีมูลค่าเพิ่ม "
                        "รอขอคืน (VAT Refundable) ก่อนล้างยอด"
                    )
                )
            line_commands.append(
                {
                    "name": reference,
                    "account_id": self.refund_account_id.id,
                    "debit": -net,
                    "credit": 0.0,
                }
            )
        if not line_commands:
            return False
        return self._od19_post_settlement_move(line_commands, reference)
