# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class Pp30Register(models.AbstractModel):
    _name = "report.od19_thai_tax_reports.pp30_register"
    _description = "PP30 (VAT Return) Register"

    def _od19_input_vat_split(self, move, non_deductible_group):
        """แยกภาษีซื้อออกเป็นส่วนที่หักได้ (นำไปลบภาษีขาย) และส่วนที่ต้องห้าม

        Section 82/5: input VAT carried by the "non-deductible" tax must be
        reported separately because it cannot be claimed against output VAT.
        """
        tax_amount = abs(move.amount_tax_signed)
        non_deductible = 0.0
        if non_deductible_group:
            for tax_line in move.line_ids.filtered("tax_line_id"):
                if tax_line.tax_line_id.tax_group_id == non_deductible_group:
                    non_deductible += abs(tax_line.balance)
        if non_deductible > tax_amount:
            non_deductible = tax_amount
        return tax_amount - non_deductible, non_deductible

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")
        company = (
            self.env["res.company"].browse(company_id)
            if company_id
            else self.env.company
        )

        non_deductible_group = self.env.ref(
            "od19_thai_tax_reports.tax_group_vat_non_deductible",
            raise_if_not_found=False,
        )

        base_domain = [
            ("state", "=", "posted"),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
        ]
        if company_id:
            base_domain.append(("company_id", "=", company_id))

        # ------------------------------------------------------------------
        # 1) ภาษีขาย (Output VAT) - ใบกำกับภาษีขาย / ใบลดหนี้
        # ------------------------------------------------------------------
        sales_moves = self.env["account.move"].search(
            base_domain + [("move_type", "in", ("out_invoice", "out_refund"))],
            order="invoice_date, name",
        )
        sales_lines = []
        sales_base = 0.0
        output_vat = 0.0
        for move in sales_moves:
            if not move.amount_tax_signed:
                continue
            # ใบลดหนี้ (out_refund) แสดงเป็นค่าลบเพื่อหักกลบภาษีขาย
            sign = 1.0 if move.move_type == "out_invoice" else -1.0
            tax_base = sign * abs(move.amount_untaxed_signed)
            vat_amount = sign * abs(move.amount_tax_signed)
            sales_lines.append(
                {
                    "invoice_date": move.invoice_date,
                    "name": move.name,
                    "partner_name": move.partner_id.name or "",
                    "partner_vat": move.partner_id.vat or "",
                    "tax_base": tax_base,
                    "vat_amount": vat_amount,
                }
            )
            sales_base += tax_base
            output_vat += vat_amount

        # ------------------------------------------------------------------
        # 2) ภาษีซื้อ (Input VAT) - ใบกำกับภาษีซื้อ / ใบลดหนี้ผู้ขาย
        # ------------------------------------------------------------------
        purchase_moves = self.env["account.move"].search(
            base_domain + [("move_type", "in", ("in_invoice", "in_refund"))],
            order="invoice_date, name",
        )
        purchase_lines = []
        purchase_base = 0.0
        input_vat = 0.0
        non_deductible_vat = 0.0
        for move in purchase_moves:
            if not move.amount_tax_signed:
                continue
            sign = 1.0 if move.move_type == "in_invoice" else -1.0
            tax_base = sign * abs(move.amount_untaxed_signed)
            deductible, non_deductible = self._od19_input_vat_split(
                move, non_deductible_group
            )
            purchase_lines.append(
                {
                    "invoice_date": move.invoice_date,
                    "name": move.name,
                    "partner_name": move.partner_id.name or "",
                    "partner_vat": move.partner_id.vat or "",
                    "tax_base": tax_base,
                    "vat_amount": sign * deductible,
                    "non_deductible_amount": sign * non_deductible,
                }
            )
            purchase_base += tax_base
            input_vat += sign * deductible
            non_deductible_vat += sign * non_deductible

        # ------------------------------------------------------------------
        # 3) กระทบยอดภาษีขาย / ภาษีซื้อ
        # ------------------------------------------------------------------
        # net_vat > 0 = ต้องชำระ, net_vat < 0 = ชำระเกิน (ยกไปเครดิตเดือนถัดไป)
        net_vat = output_vat - input_vat

        return {
            "doc_ids": (sales_moves | purchase_moves).ids,
            "doc_model": "account.move",
            "docs": sales_moves | purchase_moves,
            "date_from": date_from,
            "date_to": date_to,
            "company": company,
            "sales_lines": sales_lines,
            "purchase_lines": purchase_lines,
            "sales_base": sales_base,
            "output_vat": output_vat,
            "purchase_base": purchase_base,
            "input_vat": input_vat,
            "non_deductible_vat": non_deductible_vat,
            "net_vat": net_vat,
            "vat_payable": net_vat if net_vat > 0.0 else 0.0,
            "vat_overpaid": -net_vat if net_vat < 0.0 else 0.0,
        }
