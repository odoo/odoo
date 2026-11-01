# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_bot_url = fields.Char(
        string="BOT URL (รายการภาษี)",
        default="https://www.rd.go.th/",
        help="Base URL of the Revenue Department (BOT) e-Tax invoice lookup. "
        "The invoice number is appended as ?id=<invoice_name>.",
    )

    od19_require_vendor_bill_for_payment = fields.Boolean(
        string="บังคับตั้งหนี้ก่อนจ่าย (AP)",
        default=True,
        help="When enabled, an outbound (vendor) payment cannot be posted unless "
        "it is generated from a Vendor Bill (ตั้งหนี้). Standalone vendor "
        "payments that are not linked to any bill are blocked.",
    )

    # ------------------------------------------------------------------
    # Default control accounts for the period-clearing wizards
    # (VAT ภ.พ.30 / WHT / Suspense-Intercompany)
    # ------------------------------------------------------------------
    od19_vat_output_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Output VAT Account (ภาษีขาย)",
        help="Control account accumulating output VAT (ภาษีขาย).",
    )
    od19_vat_input_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Input VAT Account (ภาษีซื้อ)",
        help="Control account accumulating input VAT (ภาษีซื้อ).",
    )
    od19_vat_settlement_account_id = fields.Many2one(
        comodel_name="account.account",
        string="VAT Payable Account (ภาษีมูลค่าเพิ่มค้างจ่าย)",
        help="Account receiving the net VAT payable at period close (ภ.พ.30).",
    )
    od19_vat_refund_account_id = fields.Many2one(
        comodel_name="account.account",
        string="VAT Refundable Account (ภาษีมูลค่าเพิ่มรอขอคืน)",
        help="Account receiving the net VAT refundable when input VAT exceeds "
        "output VAT.",
    )
    od19_wht_payable_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="od19_company_wht_payable_rel",
        column1="company_id",
        column2="account_id",
        string="WHT Payable Accounts (ภาษีหัก ณ ที่จ่ายค้างจ่าย)",
        help="Control accounts accumulating withholding tax payable per rate.",
    )
    od19_wht_settlement_account_id = fields.Many2one(
        comodel_name="account.account",
        string="WHT to Remit Account (ภาษีหัก ณ ที่จ่ายนำส่ง)",
        help="Account receiving the consolidated WHT payable before remitting "
        "to the Revenue Department (ภ.ง.ด.3 / ภ.ง.ด.53).",
    )
    od19_suspense_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="od19_company_suspense_rel",
        column1="company_id",
        column2="account_id",
        string="Suspense Accounts (บัญชีพัก)",
        help="Suspense / pending-investigation accounts cleared at period close.",
    )
    od19_intercompany_account_ids = fields.Many2many(
        comodel_name="account.account",
        relation="od19_company_intercompany_rel",
        column1="company_id",
        column2="account_id",
        string="Intercompany Accounts (บัญชีระหว่างบริษัท)",
        help="Intercompany due to / due from accounts reconciled at period close.",
    )
