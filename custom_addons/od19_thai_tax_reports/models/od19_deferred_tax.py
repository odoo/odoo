# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""TAS 12 — ภาษีเงินได้รอตัดบัญชี (deferred tax).

โมดูลนี้ออกแบบตามแนวทาง worksheet ซึ่งเป็นวิธีที่ผู้สอบบัญชีใช้จริง:
ผู้ใช้บันทึกรายการผลต่างชั่วคราว (temporary difference) ระหว่าง
**มูลค่าตามบัญชี** (carrying amount) กับ **ฐานภาษี** (tax base) แยกตามหมวด
ระบบจะคำนวณ :

* **ผลต่างชั่วคราวที่ต้องเสียภาษี** (taxable temporary difference) — เมื่อ
  มูลค่าตามบัญชี > ฐานภาษี → รับรู้เป็น **สินทรัพย์ภาษีเงินได้รอตัดบัญชี**
  ฝั่งหนี้สิน (deferred tax liability, DTL)
* **ผลต่างชั่วคราวที่หักได้** (deductible temporary difference) — เมื่อ
  มูลค่าตามบัญชี < ฐานภาษี → รับรู้เป็น **สินทรัพย์ภาษีเงินได้รอตัดบัญชี**
  (deferred tax asset, DTA)

การรับรู้รายการบัญชีจะบันทึกเฉพาะ **ส่วนเคลื่อนไหว** (movement) ระหว่างยอด
ยกมาของงวดก่อนกับยอดปิดงวดปัจจุบัน ตามหลักการของ TAS 12 เพื่อไม่ให้รับรู้
ซ้ำในแต่ละรอบระยะเวลา
"""

from odoo import api, fields, models
from odoo.exceptions import UserError


class Od19DeferredTaxWorksheet(models.Model):
    _name = "od19.deferred.tax.worksheet"
    _description = "TAS 12 Deferred Tax Worksheet"
    _inherit = ["mail.thread"]
    _order = "date_to desc, id desc"

    name = fields.Char(
        string="Worksheet Reference",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    date_from = fields.Date(
        string="Period From",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(month=1, day=1),
    )
    date_to = fields.Date(
        string="Reporting Date",
        required=True,
        default=fields.Date.context_today,
        help="วันที่รายงาน (ปกติคือวันสิ้นรอบระยะเวลาบัญชี)",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted")],
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    line_ids = fields.One2many(
        "od19.deferred.tax.line",
        "worksheet_id",
        string="Temporary Differences",
        copy=True,
    )
    previous_worksheet_id = fields.Many2one(
        "od19.deferred.tax.worksheet",
        string="Previous Worksheet",
        domain="[('company_id', '=', company_id), "
        "('state', '=', 'posted'), ('id', '!=', id)]",
        help="งวดก่อนที่ Post แล้ว ใช้เป็นยอดยกมาเพื่อคำนวณส่วนเคลื่อนไหว "
        "(เว้นว่างได้หากเป็นงวดแรก)",
    )
    journal_entry_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
    )
    posted_date = fields.Date(string="Posted On", readonly=True, copy=False)
    note = fields.Text(string="Notes")

    opening_dta = fields.Monetary(
        string="Opening DTA",
        compute="_compute_totals",
        currency_field="currency_id",
        help="ยอดสินทรัพย์ภาษีรอตัดบัญชียกมาจากงวดก่อน",
    )
    opening_dtl = fields.Monetary(
        string="Opening DTL",
        compute="_compute_totals",
        currency_field="currency_id",
        help="ยอดหนี้สินภาษีรอตัดบัญชียกมาจากงวดก่อน",
    )
    total_dta = fields.Monetary(
        string="Closing DTA",
        compute="_compute_totals",
        currency_field="currency_id",
        recursive=True,
    )
    total_dtl = fields.Monetary(
        string="Closing DTL",
        compute="_compute_totals",
        currency_field="currency_id",
        recursive=True,
    )
    net_deferred = fields.Monetary(
        string="Net Deferred Tax",
        compute="_compute_totals",
        currency_field="currency_id",
        help="บวก = สุทธิเป็นสินทรัพย์ (net DTA), ลบ = สุทธิเป็นหนี้สิน (net DTL)",
    )
    movement_dta = fields.Monetary(
        string="Movement DTA",
        compute="_compute_totals",
        currency_field="currency_id",
    )
    movement_dtl = fields.Monetary(
        string="Movement DTL",
        compute="_compute_totals",
        currency_field="currency_id",
    )
    movement_expense = fields.Monetary(
        string="Deferred Tax Expense",
        compute="_compute_totals",
        currency_field="currency_id",
        help="ค่าใช้จ่ายภาษีรอตัดบัญชีของงวด (movement DTL - movement DTA)",
    )

    dta_account_id = fields.Many2one(
        "account.account",
        string="Deferred Tax Asset Account",
        related="company_id.od19_deferred_tax_asset_account_id",
    )
    dtl_account_id = fields.Many2one(
        "account.account",
        string="Deferred Tax Liability Account",
        related="company_id.od19_deferred_tax_liability_account_id",
    )
    expense_account_id = fields.Many2one(
        "account.account",
        string="Deferred Tax Expense Account",
        related="company_id.od19_deferred_tax_expense_account_id",
    )

    # ------------------------------------------------------------------
    # Naming
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "od19.deferred.tax.worksheet"
                    )
                    or "New"
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------
    @api.depends(
        "line_ids.difference_type",
        "line_ids.deferred_tax_amount",
        "previous_worksheet_id.total_dta",
        "previous_worksheet_id.total_dtl",
    )
    def _compute_totals(self):
        for worksheet in self:
            total_dta = sum(
                line.deferred_tax_amount
                for line in worksheet.line_ids
                if line.difference_type == "deductible"
            )
            total_dtl = sum(
                line.deferred_tax_amount
                for line in worksheet.line_ids
                if line.difference_type == "taxable"
            )
            previous = worksheet.previous_worksheet_id
            opening_dta = previous.total_dta if previous else 0.0
            opening_dtl = previous.total_dtl if previous else 0.0

            worksheet.total_dta = total_dta
            worksheet.total_dtl = total_dtl
            worksheet.opening_dta = opening_dta
            worksheet.opening_dtl = opening_dtl
            worksheet.net_deferred = total_dta - total_dtl
            worksheet.movement_dta = total_dta - opening_dta
            worksheet.movement_dtl = total_dtl - opening_dtl
            worksheet.movement_expense = (
                worksheet.movement_dtl - worksheet.movement_dta
            )

    # ------------------------------------------------------------------
    # Journal entry
    # ------------------------------------------------------------------
    def action_post_deferred_tax(self):
        """รับรู้ส่วนเคลื่อนไหวของภาษีรอตัดบัญชีเป็นรายการสมุดรายวัน"""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(self.env._("รายการนี้ถูกบันทึกบัญชีไปแล้ว"))

        company = self.company_id
        move, dtl_amount, dta_amount = self._prepare_journal_entry()
        if not move:
            raise UserError(
                self.env._(
                    "ยังไม่มีการตั้งค่าบัญชีภาษีเงินได้รอตัดบัญชี "
                    "(สินทรัพย์/หนี้สิน/ค่าใช้จ่าย) สำหรับบริษัท %s "
                    "กรุณาตั้งค่าในหน้าตั้งค่าบริษัทก่อน",
                    company.display_name,
                )
            )
        if not dtl_amount and not dta_amount:
            raise UserError(
                self.env._("ไม่มีการเปลี่ยนแปลงของภาษีรอตัดบัญชีในงวดนี้")
            )

        move.action_post()
        self.write(
            {
                "state": "posted",
                "journal_entry_id": move.id,
                "posted_date": fields.Date.context_today(self),
            }
        )
        self.message_post(
            body=self.env._(
                "บันทึกบัญชีภาษีรอตัดบัญชี (TAS 12) — หนี้สินเพิ่ม/ลด %(dtl)s, "
                "สินทรัพย์เพิ่ม/ลด %(dta)s",
                dtl=dtl_amount,
                dta=dta_amount,
            )
        )
        return True

    def _prepare_journal_entry(self):
        """สร้าง account.move ของส่วนเคลื่อนไหว (ยังไม่ Post)"""
        self.ensure_one()
        company = self.company_id
        dta_account = company.od19_deferred_tax_asset_account_id
        dtl_account = company.od19_deferred_tax_liability_account_id
        expense_account = company.od19_deferred_tax_expense_account_id
        if not (dta_account and dtl_account and expense_account):
            return self.env["account.move"], 0.0, 0.0

        movement_dtl = self.movement_dtl
        movement_dta = self.movement_dta
        lines = []

        if movement_dtl:
            if movement_dtl > 0:
                lines.append(
                    (0, 0, {
                        "name": self.env._("หนี้สินภาษีเงินได้รอตัดบัญชีเพิ่มขึ้น"),
                        "account_id": dtl_account.id,
                        "credit": movement_dtl,
                    })
                )
            else:
                lines.append(
                    (0, 0, {
                        "name": self.env._("หนี้สินภาษีเงินได้รอตัดบัญชีลดลง"),
                        "account_id": dtl_account.id,
                        "debit": -movement_dtl,
                    })
                )

        if movement_dta:
            if movement_dta > 0:
                lines.append(
                    (0, 0, {
                        "name": self.env._("สินทรัพย์ภาษีเงินได้รอตัดบัญชีเพิ่มขึ้น"),
                        "account_id": dta_account.id,
                        "debit": movement_dta,
                    })
                )
            else:
                lines.append(
                    (0, 0, {
                        "name": self.env._("สินทรัพย์ภาษีเงินได้รอตัดบัญชีลดลง"),
                        "account_id": dta_account.id,
                        "credit": -movement_dta,
                    })
                )

        deferred_expense = movement_dtl - movement_dta
        if deferred_expense > 0:
            lines.append(
                (0, 0, {
                    "name": self.env._("ค่าใช้จ่ายภาษีเงินได้รอตัดบัญชี"),
                    "account_id": expense_account.id,
                    "debit": deferred_expense,
                })
            )
        elif deferred_expense < 0:
            lines.append(
                (0, 0, {
                    "name": self.env._("รายได้ภาษีเงินได้รอตัดบัญชี"),
                    "account_id": expense_account.id,
                    "credit": -deferred_expense,
                })
            )

        journal = company.od19_deferred_tax_journal_id or self.env[
            "account.journal"
        ].search(
            [("type", "=", "general"), ("company_id", "=", company.id)],
            limit=1,
        )
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": self.date_to,
                "journal_id": journal.id,
                "ref": self.name,
                "line_ids": lines,
            }
        )
        return move, movement_dtl, movement_dta

    def action_view_journal_entry(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.journal_entry_id.id,
            "view_mode": "form",
            "target": "current",
        }


class Od19DeferredTaxLine(models.Model):
    _name = "od19.deferred.tax.line"
    _description = "TAS 12 Deferred Tax Line"
    _order = "sequence, id"

    worksheet_id = fields.Many2one(
        "od19.deferred.tax.worksheet",
        string="Worksheet",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        related="worksheet_id.company_id", store=True, readonly=True
    )
    currency_id = fields.Many2one(
        related="worksheet_id.currency_id", readonly=True
    )
    name = fields.Char(string="Description", required=True)
    category = fields.Selection(
        [
            ("fixed_asset", "สินทรัพย์ถาวร (ค่าเสื่อมราคา)"),
            ("provision", "ประมาณการหนี้สิน / เงินสำรอง"),
            ("allowance", "ค่าเผื่อหนี้สงสัยจะสูญ"),
            ("inventory", "สินค้าคงเหลือ"),
            ("other", "อื่น ๆ"),
        ],
        string="Category",
        default="other",
        required=True,
    )
    carrying_amount = fields.Monetary(
        string="Carrying Amount",
        currency_field="currency_id",
        help="มูลค่าตามบัญชี (accounting base)",
    )
    tax_base = fields.Monetary(
        string="Tax Base",
        currency_field="currency_id",
        help="ฐานภาษี (tax base)",
    )
    difference = fields.Monetary(
        string="Temporary Difference",
        compute="_compute_difference",
        currency_field="currency_id",
        help="มูลค่าตามบัญชี - ฐานภาษี",
    )
    difference_type = fields.Selection(
        [
            ("taxable", "ผลต่างที่ต้องเสียภาษี (Taxable)"),
            ("deductible", "ผลต่างที่หักได้ (Deductible)"),
            ("none", "ไม่มีผลต่าง"),
        ],
        string="Difference Type",
        compute="_compute_difference",
    )
    tax_rate = fields.Float(
        string="Tax Rate (%)",
        default=lambda self: self.env.company.od19_deferred_tax_rate,
        digits=(5, 2),
    )
    deferred_tax_amount = fields.Monetary(
        string="Deferred Tax",
        compute="_compute_deferred_tax",
        currency_field="currency_id",
        help="ผลต่างชั่วคราว (ค่าสัมบูรณ์) x อัตราภาษี",
    )

    @api.depends("carrying_amount", "tax_base")
    def _compute_difference(self):
        for line in self:
            difference = (line.carrying_amount or 0.0) - (line.tax_base or 0.0)
            line.difference = difference
            if difference > 0:
                line.difference_type = "taxable"
            elif difference < 0:
                line.difference_type = "deductible"
            else:
                line.difference_type = "none"

    @api.depends("difference", "tax_rate")
    def _compute_deferred_tax(self):
        for line in self:
            line.deferred_tax_amount = (
                abs(line.difference or 0.0) * (line.tax_rate or 0.0) / 100.0
            )
