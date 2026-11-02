# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class TaxReportWizard(models.TransientModel):
    _name = "thai.tax.report.wizard"
    _description = "Thai Tax Report Wizard"

    date_from = fields.Date(
        string="From Date",
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string="To Date",
        required=True,
        default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    report_type = fields.Selection(
        [
            ("vat_sales", "VAT Sales Register (สมุดรายการภาษีขาย)"),
            ("vat_purchase", "VAT Purchase Register (สมุดรายการภาษีซื้อ)"),
            ("wht", "WHT Register (สมุดภาษีหัก ณ ที่จ่าย)"),
            ("pp30", "PP30 Register (แบบแสดงรายการภาษีมูลค่าเพิ่ม ภ.พ.30)"),
            ("pp36", "PP36 Register (รายงานภาษีนำส่ง ภ.พ.36)"),
            ("pnd3", "PND3 Register (แบบแสดงรายการ ภ.ง.ด.3)"),
            ("pnd53", "PND53 Register (แบบแสดงรายการ ภ.ง.ด.53)"),
            ("pnd54", "PND54 Register (แบบแสดงรายการ ภ.ง.ด.54)"),
            ("pnd50", "PND50 Register (แบบแสดงรายการ ภ.ง.ด.50)"),
            ("pnd51", "PND51 Register (แบบแสดงรายการ ภ.ง.ด.51)"),
            ("npae", "NPAE Financial Statement (งบการเงินตามแบบ NPAE)"),
            ("sbc3", "SBC3 Financial Statement (งบการเงินนำส่ง DBD ส.บช.3)"),
            ("sbt_pp40", "PP40 SBT Register (รายงานภาษีธุรกิจเฉพาะ ภ.ธ.40)"),
            ("stamp_duty", "Stamp Duty Register (ทะเบียนอากรแสตมป์)"),
        ],
        string="Report Type",
        required=True,
        default="vat_sales",
    )

    def action_print(self):
        self.ensure_one()
        report_map = {
            "vat_sales": "od19_thai_tax_reports.action_vat_sales_register",
            "vat_purchase": "od19_thai_tax_reports.action_vat_purchase_register",
            "wht": "od19_thai_tax_reports.action_wht_register",
            "pp30": "od19_thai_tax_reports.action_pp30_register",
            "pp36": "od19_thai_tax_reports.action_pp36_register",
            "pnd3": "od19_thai_tax_reports.action_pnd3_register",
            "pnd53": "od19_thai_tax_reports.action_pnd53_register",
            "pnd54": "od19_thai_tax_reports.action_pnd54_register",
            "pnd50": "od19_thai_tax_reports.action_pnd50_register",
            "pnd51": "od19_thai_tax_reports.action_pnd51_register",
            "npae": "od19_thai_tax_reports.action_npae_financial_statement",
            "sbc3": "od19_thai_tax_reports.action_sbc3_register",
            "sbt_pp40": "od19_thai_tax_reports.action_sbt_pp40_register",
            "stamp_duty": "od19_thai_tax_reports.action_stamp_duty_register",
        }
        return (
            self.env.ref(report_map[self.report_type])
            .with_context(
                date_from=self.date_from,
                date_to=self.date_to,
                company_id=self.company_id.id,
            )
            .report_action(self)
        )
