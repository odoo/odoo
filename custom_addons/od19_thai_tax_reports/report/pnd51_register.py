# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class Pnd51Register(models.AbstractModel):
    """ภ.ง.ด.51 — แบบแสดงรายการภาษีเงินได้นิติบุคคล (ครึ่งปี/ประมาณการ)

    ใช้กำไร (ขาดทุน) สุทธิของรอบระยะเวลา (โดยปกติคือ 6 เดือนแรกของรอบบัญชี)
    เพื่อประมาณการกำไรสุทธิทั้งปี และคำนวณภาษีเงินได้นิติบุคคลที่ต้องชำระครึ่งปี
    ซึ่งเท่ากับ 50% ของประมาณการภาษีทั้งปี
    """

    _name = "report.od19_thai_tax_reports.pnd51_register"
    _description = "PND51 (ภาษีเงินได้นิติบุคคล ครึ่งปี) Register"

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")

        pnd50 = self.env["report.od19_thai_tax_reports.pnd50_register"]
        (
            income_lines,
            expense_lines,
            total_income,
            total_expense,
        ) = pnd50._get_profit_and_loss(date_from, date_to, company_id)
        net_profit = total_income - total_expense

        months = 1
        if date_from and date_to:
            months = (
                (date_to.year - date_from.year) * 12
                + (date_to.month - date_from.month)
                + 1
            )
        months = max(months, 1)

        estimated_annual_profit = net_profit * 12.0 / months
        taxable_annual_profit = (
            estimated_annual_profit if estimated_annual_profit > 0 else 0.0
        )
        estimated_annual_tax = taxable_annual_profit * pnd50.TAX_RATE
        half_year_payable = estimated_annual_tax * 0.5

        return {
            "doc_ids": docids,
            "doc_model": "thai.tax.report.wizard",
            "docs": self.env["thai.tax.report.wizard"].browse(docids),
            "date_from": date_from,
            "date_to": date_to,
            "company": (
                self.env["res.company"].browse(company_id)
                if company_id
                else self.env.company
            ),
            "income_lines": income_lines,
            "expense_lines": expense_lines,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_profit": net_profit,
            "months": months,
            "estimated_annual_profit": estimated_annual_profit,
            "taxable_annual_profit": taxable_annual_profit,
            "tax_rate_percent": pnd50.TAX_RATE * 100.0,
            "estimated_annual_tax": estimated_annual_tax,
            "half_year_payable": half_year_payable,
        }
