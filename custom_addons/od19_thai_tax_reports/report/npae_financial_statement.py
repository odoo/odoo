# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""TFRS for NPAEs — งบการเงินสำหรับกิจการที่ไม่มีส่วนได้เสียสาธารณะ.

รายงานนี้จัดทำงบการเงินตามแนวทาง TFRS for NPAEs (Non-Publicly Accountable
Entities) ประกอบด้วย:

* **งบแสดงฐานะการเงิน** (Statement of Financial Position) — สินทรัพย์ หนี้สิน
  และส่วนของผู้ถือหุ้น ณ วันสิ้นรอบระยะเวลา (ยอดสะสมถึง ``date_to``)
* **งบกำไรขาดทุน** (Statement of Profit or Loss) — รายได้และค่าใช้จ่ายภายใน
  รอบระยะเวลา (``date_from`` ถึง ``date_to``)

ยอดทั้งหมดอ่านจาก ``account.move.line`` ที่ ``parent_state = 'posted'`` เท่านั้น
และแปลงเครื่องหมายให้เป็น "ด้านบวก" ตามธรรมชาติของแต่ละหมวดบัญชี
(สินทรัพย์/ค่าใช้จ่ายเป็นเดบิต, หนี้สิน/ส่วนของผู้ถือหุ้น/รายได้เป็นเครดิต)
"""

from odoo import models

ASSET_CURRENT_TYPES = (
    "asset_receivable",
    "asset_cash",
    "asset_current",
    "asset_prepayments",
)
ASSET_NON_CURRENT_TYPES = ("asset_non_current", "asset_fixed")
LIABILITY_CURRENT_TYPES = (
    "liability_payable",
    "liability_credit_card",
    "liability_current",
)
LIABILITY_NON_CURRENT_TYPES = ("liability_non_current",)
EQUITY_TYPES = ("equity", "equity_unaffected")
INCOME_TYPES = ("income", "income_other")
EXPENSE_TYPES = (
    "expense",
    "expense_other",
    "expense_depreciation",
    "expense_direct_cost",
)


class NpaeFinancialStatement(models.AbstractModel):
    """TFRS for NPAEs — งบการเงินตามแบบ NPAE"""

    _name = "report.od19_thai_tax_reports.npae_financial_statement"
    _description = "TFRS for NPAEs Financial Statement"

    def _read_lines(
        self,
        account_types,
        date_from,
        date_to,
        company_id,
        credit_positive=False,
    ):
        """สรุปยอดคงเหลือแยกตามบัญชีสำหรับกลุ่ม ``account_types`` ที่กำหนด

        ``credit_positive`` ใช้แปลงเครื่องหมายสำหรับหมวดที่เป็นเครดิต
        (หนี้สิน/ส่วนของผู้ถือหุ้น/รายได้) ให้แสดงเป็นค่าบวก
        """
        domain = [
            ("account_id.account_type", "in", list(account_types)),
            ("parent_state", "=", "posted"),
        ]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        if company_id:
            domain.append(("company_id", "=", company_id))

        lines = []
        total = 0.0
        groups = self.env["account.move.line"]._read_group(
            domain, ["account_id"], ["balance:sum"]
        )
        for account, balance in groups:
            if not account:
                continue
            amount = -balance if credit_positive else balance
            lines.append(
                {
                    "code": account.code or "",
                    "name": account.name or "",
                    "amount": amount,
                }
            )
            total += amount
        lines.sort(key=lambda line: line["code"])
        return lines, total

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")

        # งบแสดงฐานะการเงิน — ยอดสะสม ณ วันสิ้นรอบระยะเวลา
        assets_current, total_assets_current = self._read_lines(
            ASSET_CURRENT_TYPES, None, date_to, company_id
        )
        assets_non_current, total_assets_non_current = self._read_lines(
            ASSET_NON_CURRENT_TYPES, None, date_to, company_id
        )
        liabilities_current, total_liabilities_current = self._read_lines(
            LIABILITY_CURRENT_TYPES, None, date_to, company_id, credit_positive=True
        )
        (
            liabilities_non_current,
            total_liabilities_non_current,
        ) = self._read_lines(
            LIABILITY_NON_CURRENT_TYPES,
            None,
            date_to,
            company_id,
            credit_positive=True,
        )
        equity_lines, total_equity = self._read_lines(
            EQUITY_TYPES, None, date_to, company_id, credit_positive=True
        )

        # งบกำไรขาดทุน — ยอดเฉพาะรอบระยะเวลา
        income_lines, total_income = self._read_lines(
            INCOME_TYPES, date_from, date_to, company_id, credit_positive=True
        )
        expense_lines, total_expense = self._read_lines(
            EXPENSE_TYPES, date_from, date_to, company_id
        )

        total_assets = total_assets_current + total_assets_non_current
        total_liabilities = (
            total_liabilities_current + total_liabilities_non_current
        )
        net_profit = total_income - total_expense
        total_equity_with_result = total_equity + net_profit
        total_liabilities_equity = total_liabilities + total_equity_with_result
        balance_difference = total_assets - total_liabilities_equity

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
            "assets_current": assets_current,
            "total_assets_current": total_assets_current,
            "assets_non_current": assets_non_current,
            "total_assets_non_current": total_assets_non_current,
            "total_assets": total_assets,
            "liabilities_current": liabilities_current,
            "total_liabilities_current": total_liabilities_current,
            "liabilities_non_current": liabilities_non_current,
            "total_liabilities_non_current": total_liabilities_non_current,
            "total_liabilities": total_liabilities,
            "equity_lines": equity_lines,
            "total_equity": total_equity,
            "total_equity_with_result": total_equity_with_result,
            "total_liabilities_equity": total_liabilities_equity,
            "balance_difference": balance_difference,
            "income_lines": income_lines,
            "total_income": total_income,
            "expense_lines": expense_lines,
            "total_expense": total_expense,
            "net_profit": net_profit,
        }
