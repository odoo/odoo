# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class Pnd3Register(models.AbstractModel):
    """ภ.ง.ด.3 register — withholding tax deducted from payments made to
    individuals (บุคคลธรรมดา).

    The OCA ``l10n_th_account_tax`` module flags withholding types with the
    income tax form they belong to (pnd1/pnd2/pnd3/pnd3a/pnd53). The monthly
    ภ.ง.ด.3 return and its annual ภ.ง.ด.3a variant both cover payments to
    individuals, so both flags are gathered here.
    """

    _name = "report.od19_thai_tax_reports.pnd3_register"
    _description = "PND3 (ภ.ง.ด.3) Register"

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")

        domain = [
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("wht_tax_id.income_tax_form", "in", ["pnd3", "pnd3a"]),
            ("cancelled", "=", False),
        ]
        if company_id:
            domain.append(("company_id", "=", company_id))

        wht_moves = self.env["account.withholding.move"].search(
            domain, order="date, id"
        )

        lines = []
        total_base = 0.0
        total_wht = 0.0

        for wht in wht_moves:
            base = wht.amount_income or 0.0
            wht_amt = wht.amount_wht or 0.0
            payment = wht.payment_id
            lines.append(
                {
                    "date": wht.date,
                    "name": payment.name if payment else wht.move_id.name,
                    "partner_name": wht.partner_id.name or "",
                    "partner_vat": wht.partner_id.vat or "",
                    "income_type": wht.wht_cert_income_desc or "",
                    "wht_percent": wht.wht_tax_id.amount if wht.wht_tax_id else 0.0,
                    "base_amount": base,
                    "wht_amount": wht_amt,
                }
            )
            total_base += base
            total_wht += wht_amt

        return {
            "doc_ids": wht_moves.ids,
            "doc_model": "account.withholding.move",
            "docs": wht_moves,
            "date_from": date_from,
            "date_to": date_to,
            "company": (
                self.env["res.company"].browse(company_id)
                if company_id
                else self.env.company
            ),
            "lines": lines,
            "total_base": total_base,
            "total_wht": total_wht,
        }
