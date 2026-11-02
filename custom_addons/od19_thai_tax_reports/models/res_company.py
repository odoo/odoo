# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_enforce_86_4_validation = fields.Boolean(
        string="ตรวจสอบรายการใบกำกับภาษีเต็มรูป (ม.86/4)",
        default=True,
        help="เมื่อเปิดใช้งาน ระบบจะตรวจสอบว่าใบกำกับภาษีขายเต็มรูป "
        "(ขายให้นิติบุคคลที่มีเลขประจำตัวผู้เสียภาษี) มีรายการครบทั้ง 8 ข้อ "
        "ตามมาตรา 86/4 แห่งประมวลรัษฎากร ก่อนอนุญาตให้ Post เอกสาร",
    )

    od19_ewht_enabled = fields.Boolean(
        string="e-Withholding Tax (e-WHT)",
        help="นำส่งภาษีหัก ณ ที่จ่ายอิเล็กทรอนิกส์ผ่านธนาคาร "
        "สำหรับบริษัทนี้",
    )
    od19_ewht_mode = fields.Selection(
        [("mock", "Mock (ทดสอบ)"), ("live", "Live (ธนาคาร)")],
        string="e-WHT Submission Channel",
        default="mock",
        required=True,
        help="Mock ตอบกลับภายในระบบและเป็นค่าเริ่มต้น จนกว่าจะได้ API "
        "contract ของธนาคาร ส่วน Live จะส่งข้อมูลไปยัง endpoint จริง",
    )
    od19_ewht_endpoint = fields.Char(
        string="e-WHT Bank Endpoint",
        help="Base URL ของบริการ e-Withholding Tax ของธนาคาร",
    )
    od19_ewht_provider_id = fields.Char(
        string="e-WHT Service Provider ID",
        help="รหัสผู้ให้บริการ (Service Provider ID) ที่ธนาคารออกให้กับบริษัทนี้",
    )

    od19_deferred_tax_asset_account_id = fields.Many2one(
        "account.account",
        string="บัญชีสินทรัพย์ภาษีเงินได้รอตัดบัญชี (DTA)",
        domain="[('internal_group', '=', 'asset')]",
        help="บัญชีที่ใช้บันทึกสินทรัพย์ภาษีเงินได้รอตัดบัญชี (TAS 12)",
    )
    od19_deferred_tax_liability_account_id = fields.Many2one(
        "account.account",
        string="บัญชีหนี้สินภาษีเงินได้รอตัดบัญชี (DTL)",
        domain="[('internal_group', '=', 'liability')]",
        help="บัญชีที่ใช้บันทึกหนี้สินภาษีเงินได้รอตัดบัญชี (TAS 12)",
    )
    od19_deferred_tax_expense_account_id = fields.Many2one(
        "account.account",
        string="บัญชีค่าใช้จ่ายภาษีเงินได้รอตัดบัญชี",
        domain="[('internal_group', '=', 'expense')]",
        help="บัญชีที่ใช้บันทึกค่าใช้จ่าย/รายได้ภาษีเงินได้รอตัดบัญชี (TAS 12)",
    )
    od19_deferred_tax_journal_id = fields.Many2one(
        "account.journal",
        string="สมุดรายวันภาษีเงินได้รอตัดบัญชี",
        domain="[('type', '=', 'general')]",
        help="สมุดรายวันสำหรับบันทึกรายการภาษีเงินได้รอตัดบัญชี "
        "(เว้นว่างได้ ระบบจะใช้สมุดรายวันทั่วไปลำดับแรก)",
    )
    od19_deferred_tax_rate = fields.Float(
        string="อัตราภาษีเงินได้รอตัดบัญชี (%)",
        default=20.0,
        digits=(5, 2),
        help="อัตราภาษีเงินได้นิติบุคคลที่ใช้คำนวณภาษีรอตัดบัญชี (ค่าเริ่มต้น 20%)",
    )

    def _od19_ewht_check_enabled(self):
        """Raise when this company has not enabled the e-Withholding feature.

        ``od19_ewht_enabled`` is the single switch of the e-WHT submission: it
        guards the creation of submissions and every step of their lifecycle,
        so nothing can be filed for a company that never opted in.
        """
        self.ensure_one()
        if not self.od19_ewht_enabled:
            raise UserError(
                self.env._(
                    "e-Withholding Tax is not enabled for company %s. Enable it "
                    "in the company settings before filing withholding records.",
                    self.display_name,
                )
            )
