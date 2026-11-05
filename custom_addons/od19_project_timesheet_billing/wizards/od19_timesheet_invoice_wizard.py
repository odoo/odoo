from odoo import _, fields, models
from odoo.exceptions import UserError


class Od19TimesheetInvoiceWizard(models.TransientModel):
    """เรียกเก็บค่าบริการจาก Timesheet (Timesheet → Invoice)

    G-12 (WS-13): ให้ผู้ใช้เลือกใบสั่งขายและช่วงวันที่ แล้วสร้างใบแจ้งหนี้จาก
    Timesheet ที่ยังไม่ถูกเรียกเก็บ โดยอาศัยกลไกมาตรฐานของ ``sale_timesheet``
    (``_recompute_qty_to_invoice`` + ``_create_invoices``) เพื่อให้จำนวน,
    ใบแจ้งหนี้ และการเชื่อม Timesheet ยังคงสอดคล้องกับ flow มาตรฐาน
    """

    _name = "od19.timesheet.invoice.wizard"
    _description = "Invoice Timesheets (Timesheet → Invoice)"

    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        string="Sales Orders",
        domain="[('state', '=', 'sale')]",
        help="เลือกใบสั่งขายที่ยืนยันแล้วซึ่งต้องการเรียกเก็บจาก Timesheet",
    )
    date_start = fields.Date(
        string="Start Date",
        help="เรียกเก็บเฉพาะ Timesheet ที่ยังไม่ถูกเรียกเก็บภายในช่วงวันที่นี้ "
             "(เว้นว่าง = ทั้งหมด)",
    )
    date_end = fields.Date(
        string="End Date",
        help="เรียกเก็บเฉพาะ Timesheet ที่ยังไม่ถูกเรียกเก็บภายในช่วงวันที่นี้ "
             "(เว้นว่าง = ทั้งหมด)",
    )

    def action_create_invoices(self):
        self.ensure_one()
        orders = self.sale_order_ids.filtered(lambda order: order.state == "sale")
        if not orders:
            raise UserError(_("เลือกใบสั่งขายที่ยืนยันแล้วอย่างน้อยหนึ่งรายการ"))
        billable_lines = orders.order_line.filtered(
            lambda sol: sol.product_id._is_delivered_timesheet()
        )
        if not billable_lines:
            raise UserError(
                _("ไม่พบรายการขายที่เรียกเก็บตามเวลาที่ใช้ (Timesheet) ในใบสั่งขายที่เลือก")
            )
        # คำนวณจำนวนที่เรียกเก็บได้ใหม่ตามช่วงวันที่ ก่อนสร้างใบแจ้งหนี้
        orders.order_line._recompute_qty_to_invoice(self.date_start, self.date_end)
        invoices = orders.with_context(
            timesheet_start_date=self.date_start,
            timesheet_end_date=self.date_end,
        )._create_invoices()
        if not invoices:
            raise UserError(_("ไม่พบ Timesheet ที่ยังไม่ถูกเรียกเก็บในช่วงที่เลือก"))
        return {
            "type": "ir.actions.act_window",
            "name": _("Invoices / ใบแจ้งหนี้"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", invoices.ids)],
        }
