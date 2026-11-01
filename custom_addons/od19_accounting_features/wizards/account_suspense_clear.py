# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class Od19AccountSuspenseClearLine(models.TransientModel):
    _name = "od19.account.suspense.clear.line"
    _description = "Suspense / Intercompany Clearing Open Item"

    wizard_id = fields.Many2one(
        comodel_name="od19.account.suspense.clear.wizard",
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


class Od19AccountSuspenseClearWizard(models.TransientModel):
    """Suspense / Intercompany Clearing (ล้างบัญชีพักและบัญชีระหว่างบริษัท).

    กระทบยอดรายการค้าง (open item) ของบัญชีพัก (suspense / บัญชีรอตรวจสอบ)
    และบัญชีระหว่างบริษัท (intercompany due to / due from) จัดกลุ่มตาม
    บัญชี+คู่ค้า แล้วล้างยอดด้วย helper กลาง เนื่องจากบัญชีเหล่านี้ต้องอาศัย
    การวินิจฉัยปลายทางของแต่ละรายการเอง wizard นี้จึงทำหน้าที่เฉพาะการ
    กระทบยอด (reconcile) ไม่สร้างรายการปิดงวดอัตโนมัติ
    """

    _name = "od19.account.suspense.clear.wizard"
    _inherit = ["od19.clear.wizard.mixin"]
    _description = "Suspense / Intercompany Clearing (บัญชีพัก)"

    suspense_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="od19_suspense_clear_account_rel",
        column1="wizard_id",
        column2="account_id",
        string="Suspense Accounts (บัญชีพัก)",
        domain="[('reconcile', '=', True), ('company_ids', 'in', company_id)]",
        default=lambda self: self.env.company.od19_suspense_account_ids.ids,
    )
    intercompany_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="od19_intercompany_clear_account_rel",
        column1="wizard_id",
        column2="account_id",
        string="Intercompany Accounts (บัญชีระหว่างบริษัท)",
        domain="[('reconcile', '=', True), ('company_ids', 'in', company_id)]",
        default=lambda self: self.env.company.od19_intercompany_account_ids.ids,
    )
    line_ids = fields.One2many(
        comodel_name="od19.account.suspense.clear.line",
        inverse_name="wizard_id",
        string="Open Items",
        readonly=True,
    )

    def _od19_control_accounts(self):
        self.ensure_one()
        return self.suspense_account_ids | self.intercompany_account_ids
