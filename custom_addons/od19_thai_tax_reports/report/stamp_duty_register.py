# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""รายงานทะเบียนอากรแสตมป์ (Stamp Duty Register).

รายงานนี้สรุปรายการอากรแสตมป์ (``od19.stamp.duty``) ที่มีวันที่ตราสาร
ภายในรอบระยะเวลา โดยแยก

* **รายละเอียดรายรายการ** — วันที่ตราสาร เลขที่ตราสาร ลักษณะแห่งตราสาร
  คู่สัญญา มูลค่าแห่งตราสาร และอากรที่ต้องชำระ
* **สรุปตามลักษณะแห่งตราสาร** — จำนวนฉบับ มูลค่ารวม และอากรรวมของแต่ละลักษณะ
* **ยอดรวมทั้งสิ้น** — มูลค่าแห่งตราสารและอากรที่ต้องชำระรวม

อัตราที่ใช้คำนวณมาจากบัญชีอัตราอากรแสตมป์ (``od19.stamp.duty.rate``)
"""

from odoo import models


class StampDutyRegister(models.AbstractModel):
    """ทะเบียนอากรแสตมป์ (Stamp Duty Register)"""

    _name = "report.od19_thai_tax_reports.stamp_duty_register"
    _description = "Stamp Duty Register"

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")

        domain = [
            ("instrument_date", ">=", date_from),
            ("instrument_date", "<=", date_to),
        ]
        if company_id:
            domain.append(("company_id", "=", company_id))

        duties = self.env["od19.stamp.duty"].search(
            domain, order="instrument_date, name"
        )

        lines = []
        total_base = 0.0
        total_duty = 0.0
        by_rate = {}

        for duty in duties:
            lines.append(
                {
                    "instrument_date": duty.instrument_date,
                    "name": duty.name,
                    "document_reference": duty.document_reference or "",
                    "rate_code": duty.rate_code or "",
                    "rate_name": duty.rate_id.name or "",
                    "partner_name": duty.partner_id.name or "",
                    "base_amount": duty.base_amount,
                    "duty_amount": duty.duty_amount,
                    "state": duty.state,
                }
            )
            total_base += duty.base_amount
            total_duty += duty.duty_amount

            key = duty.rate_id.id
            bucket = by_rate.setdefault(
                key,
                {
                    "code": duty.rate_code or "",
                    "name": duty.rate_id.name or "",
                    "count": 0,
                    "base_amount": 0.0,
                    "duty_amount": 0.0,
                },
            )
            bucket["count"] += 1
            bucket["base_amount"] += duty.base_amount
            bucket["duty_amount"] += duty.duty_amount

        return {
            "doc_ids": duties.ids,
            "doc_model": "od19.stamp.duty",
            "docs": duties,
            "date_from": date_from,
            "date_to": date_to,
            "company": (
                self.env["res.company"].browse(company_id)
                if company_id
                else self.env.company
            ),
            "lines": lines,
            "rate_summary": list(by_rate.values()),
            "total_base": total_base,
            "total_duty": total_duty,
        }
