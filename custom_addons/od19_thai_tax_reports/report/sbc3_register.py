# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""ส.บช.3 — แบบแสดงรายการนำส่งงบการเงินต่อกรมพัฒนาธุรกิจการค้า (DBD).

รายงานนี้ต่อยอดจากงบการเงิน TFRS for NPAEs ตัวเดียวกัน แล้วนำเสนอในรูปแบบ
ฟอร์ม **ส.บช.3** ที่ใช้ยื่นต่อกรมพัฒนาธุรกิจการค้า (DBD) ภายใน 150 วันนับจาก
วันสิ้นรอบระยะเวลาบัญชี (พ.ร.บ.การบัญชี พ.ศ. 2543 มาตรา 11) และต้องจัดเก็บ
งบการเงินรวมทั้งเอกสารประกอบบัญชีไว้ไม่น้อยกว่า 5 ปี (มาตรา 14)

การคำนวณยอดทั้งหมดอาศัย AbstractModel ของงบ NPAE
(``report.od19_thai_tax_reports.npae_financial_statement``) เพื่อไม่ให้ตรรกะ
การรวมยอดซ้ำซ้อนกัน แล้วเติมเฉพาะข้อมูลหัวฟอร์มที่ DBD ต้องใช้ ได้แก่
เลขทะเบียนนิติบุคคล เลขประจำตัวผู้เสียภาษี ที่อยู่ และกำหนดเวลายื่น
"""

from datetime import timedelta

from odoo import fields, models

#: กำหนดเวลายื่นงบการเงินต่อ DBD — 150 วันนับจากวันสิ้นรอบระยะเวลาบัญชี
DBD_FILING_DAYS = 150

#: ระยะเวลาจัดเก็บงบการเงินและเอกสารประกอบบัญชี (พ.ร.บ.การบัญชี 2543 ม.14)
RETENTION_YEARS = 5

#: AbstractModel ของงบการเงิน TFRS for NPAEs ที่รายงานนี้ต่อยอด
NPAE_REPORT = "report.od19_thai_tax_reports.npae_financial_statement"


class Sbc3Register(models.AbstractModel):
    """ส.บช.3 — งบการเงินนำส่งกรมพัฒนาธุรกิจการค้า (DBD)"""

    _name = "report.od19_thai_tax_reports.sbc3_register"
    _description = "SBC3 Financial Statement (DBD)"

    def _get_report_values(self, docids, data=None):
        # ใช้ผลคำนวณเดียวกับงบการเงิน TFRS for NPAEs
        values = (
            self.env[NPAE_REPORT]
            .with_context(**self.env.context)
            ._get_report_values(docids, data)
        )

        company = values["company"]
        date_to = values.get("date_to")
        filing_deadline = None
        if date_to:
            filing_deadline = fields.Date.to_date(date_to) + timedelta(
                days=DBD_FILING_DAYS
            )

        values.update(
            {
                "company_registration": company.company_registry or "",
                "company_tax_id": company.vat or "",
                "company_address": company.partner_id.contact_address or "",
                "filing_deadline": filing_deadline,
                "retention_years": RETENTION_YEARS,
            }
        )
        return values
