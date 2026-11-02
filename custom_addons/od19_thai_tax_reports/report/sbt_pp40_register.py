# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""ภ.ธ.40 — รายงานภาษีธุรกิจเฉพาะ (Specific Business Tax — SBT).

รายงานนี้สรุปรายรับที่ต้องเสียภาษีธุรกิจเฉพาะจากใบแจ้งหนี้ขาย/ใบลดหนี้ที่
``state = 'posted'`` ภายในรอบระยะเวลา โดยแยกเป็น

* **รายรับที่ต้องเสียภาษี** (tax base) — มูลค่าก่อนภาษีของรายการที่ลงภาษี SBT
* **ภาษีธุรกิจเฉพาะ 3%** และ **ภาษีส่วนท้องถิ่น 0.3%** (10% ของ SBT)
* **รวมภาษีที่ต้องนำส่ง**

ภาษีทั้งสองตัวผูกกลุ่มภาษี ``tax_group_sbt`` (สร้างใน
``data/od19_sbt_data.xml``) จึงตรวจสอบได้ว่าบรรทัดใดเป็นรายการ SBT
"""

from odoo import models

#: ภาษีธุรกิจเฉพาะหลัก (3%)
SBT_TAX_XMLID = "od19_thai_tax_reports.tax_sbt_specific"

#: ภาษีธุรกิจเฉพาะส่วนท้องถิ่น (0.3% เทียบเท่า 10% ของ SBT)
SBT_LOCAL_TAX_XMLID = "od19_thai_tax_reports.tax_sbt_local"


class SbtPp40Register(models.AbstractModel):
    """ภ.ธ.40 — ทะเบียนภาษีธุรกิจเฉพาะ"""

    _name = "report.od19_thai_tax_reports.sbt_pp40_register"
    _description = "PP40 (Specific Business Tax) Register"

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")

        sbt_tax = self.env.ref(SBT_TAX_XMLID, raise_if_not_found=False)
        sbt_local_tax = self.env.ref(SBT_LOCAL_TAX_XMLID, raise_if_not_found=False)
        sbt_taxes = (sbt_tax | sbt_local_tax)

        domain = [
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("state", "=", "posted"),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
        ]
        if company_id:
            domain.append(("company_id", "=", company_id))

        moves = self.env["account.move"].search(domain, order="invoice_date, name")

        lines = []
        total_tax_base = 0.0
        total_sbt_amount = 0.0
        total_local_amount = 0.0

        for move in moves:
            if not sbt_taxes:
                continue
            sign = -1.0 if move.move_type == "out_refund" else 1.0
            tax_base = 0.0
            sbt_amount = 0.0
            local_amount = 0.0

            for line in move.line_ids:
                # บรรทัดภาษี: ยอดภาษีที่คำนวณได้ แยกตามชนิดภาษี
                if line.tax_line_id and line.tax_line_id in sbt_taxes:
                    if line.tax_line_id == sbt_tax:
                        sbt_amount += abs(line.balance)
                    else:
                        local_amount += abs(line.balance)
                # บรรทัดรายรับที่ลงภาษี SBT: ใช้เป็นฐานภาษี
                elif not line.tax_line_id and sbt_taxes & line.tax_ids:
                    tax_base += abs(line.price_subtotal)

            if not sbt_amount and not local_amount:
                continue

            lines.append(
                {
                    "invoice_date": move.invoice_date,
                    "name": move.name,
                    "partner_name": move.partner_id.name or "",
                    "partner_vat": move.partner_id.vat or "",
                    "tax_base": sign * tax_base,
                    "sbt_amount": sign * sbt_amount,
                    "local_amount": sign * local_amount,
                    "total_amount": sign * (sbt_amount + local_amount),
                }
            )
            total_tax_base += sign * tax_base
            total_sbt_amount += sign * sbt_amount
            total_local_amount += sign * local_amount

        return {
            "doc_ids": moves.ids,
            "doc_model": "account.move",
            "docs": moves,
            "date_from": date_from,
            "date_to": date_to,
            "company": (
                self.env["res.company"].browse(company_id)
                if company_id
                else self.env.company
            ),
            "lines": lines,
            "total_tax_base": total_tax_base,
            "total_sbt_amount": total_sbt_amount,
            "total_local_amount": total_local_amount,
            "total_amount": total_sbt_amount + total_local_amount,
        }
