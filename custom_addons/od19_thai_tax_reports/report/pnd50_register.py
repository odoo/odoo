# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class Pnd50Register(models.AbstractModel):
    """ภ.ง.ด.50 — แบบแสดงรายการภาษีเงินได้นิติบุคคล (รายปี)

    รวบรวมยอดคงเหลือของบัญชีกลุ่มรายได้ (income) และค่าใช้จ่าย (expense)
    ที่ Post แล้วภายในรอบระยะเวลาบัญชี เพื่อสรุปกำไร (ขาดทุน) สุทธิตามบัญชี
    และประมาณการภาษีเงินได้นิติบุคคลในอัตรามาตรฐาน 20%

    หมายเหตุ: รายการบวกกลับ/หักออกตามประมวลรัษฎากร (เช่น ค่าใช้จ่ายต้องห้าม,
    เงินสำรอง, ผลต่างค่าเสื่อมราคาทางภาษี) ยังไม่ถูกคำนวณในรายงานนี้
    """

    _name = "report.od19_thai_tax_reports.pnd50_register"
    _description = "PND50 (ภาษีเงินได้นิติบุคคล รายปี) Register"

    TAX_RATE = 0.20

    def _get_profit_and_loss(self, date_from, date_to, company_id):
        """สรุปยอดรายได้/ค่าใช้จ่ายแยกตามบัญชี และกำไร (ขาดทุน) สุทธิตามบัญชี"""
        company = (
            self.env["res.company"].browse(company_id)
            if company_id
            else self.env.company
        )

        account_domain = [("internal_group", "in", ["income", "expense"])]
        if company_id:
            account_domain.append(("company_ids", "in", company_id))
        accounts = (
            self.env["account.account"]
            .with_company(company)
            .search(account_domain)
        )
        account_map = {account.id: account for account in accounts}

        income_lines = []
        expense_lines = []
        total_income = 0.0
        total_expense = 0.0

        if account_map:
            line_domain = [
                ("account_id", "in", list(account_map)),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("parent_state", "=", "posted"),
            ]
            if company_id:
                line_domain.append(("company_id", "=", company_id))

            groups = self.env["account.move.line"]._read_group(
                line_domain, ["account_id"], ["balance:sum"]
            )
            for account, balance in groups:
                if not account:
                    continue
                if account.internal_group == "income":
                    amount = -balance
                    income_lines.append(self._prepare_line(account, amount))
                    total_income += amount
                elif account.internal_group == "expense":
                    amount = balance
                    expense_lines.append(self._prepare_line(account, amount))
                    total_expense += amount

        income_lines.sort(key=lambda line: line["code"])
        expense_lines.sort(key=lambda line: line["code"])
        return income_lines, expense_lines, total_income, total_expense

    @staticmethod
    def _prepare_line(account, amount):
        return {
            "code": account.code or "",
            "name": account.name or "",
            "amount": amount,
        }

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")

        (
            income_lines,
            expense_lines,
            total_income,
            total_expense,
        ) = self._get_profit_and_loss(date_from, date_to, company_id)

        net_profit = total_income - total_expense
        taxable_profit = net_profit if net_profit > 0 else 0.0
        tax_amount = taxable_profit * self.TAX_RATE

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
            "taxable_profit": taxable_profit,
            "tax_rate_percent": self.TAX_RATE * 100.0,
            "tax_amount": tax_amount,
        }
