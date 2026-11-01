# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_bot_url = fields.Char(
        related="company_id.od19_bot_url",
        readonly=False,
        string="BOT URL (รายการภาษี)",
        help="Base URL of the Revenue Department (BOT) e-Tax invoice lookup. "
        "The invoice number is appended as ?id=<invoice_name>.",
    )

    od19_require_vendor_bill_for_payment = fields.Boolean(
        related="company_id.od19_require_vendor_bill_for_payment",
        readonly=False,
        string="บังคับตั้งหนี้ก่อนจ่าย (AP)",
        help="Require a Vendor Bill (ตั้งหนี้) before an outbound payment can be "
        "posted.",
    )

    # ------------------------------------------------------------------
    # Period-clearing default control accounts
    # ------------------------------------------------------------------
    od19_vat_output_account_id = fields.Many2one(
        related="company_id.od19_vat_output_account_id",
        readonly=False,
        string="Output VAT Account (ภาษีขาย)",
    )
    od19_vat_input_account_id = fields.Many2one(
        related="company_id.od19_vat_input_account_id",
        readonly=False,
        string="Input VAT Account (ภาษีซื้อ)",
    )
    od19_vat_settlement_account_id = fields.Many2one(
        related="company_id.od19_vat_settlement_account_id",
        readonly=False,
        string="VAT Payable Account (ภาษีมูลค่าเพิ่มค้างจ่าย)",
    )
    od19_vat_refund_account_id = fields.Many2one(
        related="company_id.od19_vat_refund_account_id",
        readonly=False,
        string="VAT Refundable Account (ภาษีมูลค่าเพิ่มรอขอคืน)",
    )
    od19_wht_payable_account_ids = fields.Many2many(
        related="company_id.od19_wht_payable_account_ids",
        readonly=False,
        string="WHT Payable Accounts (ภาษีหัก ณ ที่จ่ายค้างจ่าย)",
    )
    od19_wht_settlement_account_id = fields.Many2one(
        related="company_id.od19_wht_settlement_account_id",
        readonly=False,
        string="WHT to Remit Account (ภาษีหัก ณ ที่จ่ายนำส่ง)",
    )
    od19_suspense_account_ids = fields.Many2many(
        related="company_id.od19_suspense_account_ids",
        readonly=False,
        string="Suspense Accounts (บัญชีพัก)",
    )
    od19_intercompany_account_ids = fields.Many2many(
        related="company_id.od19_intercompany_account_ids",
        readonly=False,
        string="Intercompany Accounts (บัญชีระหว่างบริษัท)",
    )
