# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("l10n_br_is_avatax", "move_type", "debit_origin_id")
    def _compute_l10n_br_goods_operation_type_id(self):
        """Override."""
        self.l10n_br_goods_operation_type_id = False
        for move in self.filtered("l10n_br_is_avatax"):
            if move.debit_origin_id:
                move.l10n_br_goods_operation_type_id = self.env.ref("l10n_br_avatax.operation_type_3")  # amountComplementary
            elif move.move_type == "out_refund":
                move.l10n_br_goods_operation_type_id = self.env.ref("l10n_br_avatax.operation_type_60")  # salesReturn
            else:
                move.l10n_br_goods_operation_type_id = self.env.ref("l10n_br_avatax.operation_type_1")  # standardSales

    @api.depends("l10n_latam_document_type_id")
    def _compute_l10n_br_is_service_transaction(self):
        """account.external.tax.mixin override."""
        for move in self:
            move.l10n_br_is_service_transaction = (
                move.l10n_br_is_avatax and move.l10n_latam_document_type_id == self.env.ref("l10n_br.dt_SE")
            )

    def _get_external_taxes(self):
        """ Override of account.external.tax.mixin. """
        for invoice in self.filtered('l10n_br_is_avatax'):
            # This type of transaction requires installments with a `grossValue` before subtracted taxes. Clear any
            # already existing taxes to ensure that previous tax calculations haven't altered the down payment lines.
            if invoice.l10n_br_is_service_transaction and invoice._l10n_br_get_installments():
                invoice.invoice_line_ids.filtered('tax_ids').write({
                    'tax_ids': [Command.clear()]
                })

        return super()._get_external_taxes()

    def _l10n_br_get_origin_invoice(self):
        return self.debit_origin_id or self.reversed_entry_id

    def _l10n_br_invoice_refs_for_code(self, ref_type, document_code):
        return {
            "invoicesRefs": [
                {
                    "type": ref_type,
                    ref_type: document_code,
                }
            ]
        }

    def _l10n_br_get_invoice_refs(self):
        """account.external.tax.mixin override."""
        if origin := self._l10n_br_get_origin_invoice():
            return self._l10n_br_invoice_refs_for_code("documentCode", f"{origin._name}_{origin.id}")

        return {}

    def _l10n_br_get_installments(self):
        """account.external.tax.mixin override."""
        payments = self.line_ids.filtered(lambda line: line.display_type == "payment_term" and line.date_maturity)
        future_payments = payments.filtered(
            lambda line: line.date_maturity > (self.invoice_date or fields.Date.context_today(self))
        )
        if not future_payments:
            return None

        return {
            "installmentTerms": "1" if len(payments) == 1 else "5",
            "bill": {
                "nFat": self.name,
                "vNet": self.amount_total,
                "vOrig": self.amount_total,
            },
            "installment": [
                {
                    "documentNumber": f"{index + 1:03}",
                    "date": payment.date_maturity.isoformat(),
                    "grossValue": payment.balance,
                    "netValue": payment.balance,
                }
                for index, payment in enumerate(payments.sorted("date_maturity"))
            ],
        }

    def _l10n_br_build_avatax_line(self, product, qty, unit_price, total, discount, line_id):
        """ Override of account.external.tax.mixin. Swap out the product name for line description on invoices.
        TODO: remove this in master and provide a description directly in _get_line_data_for_external_taxes so we avoid
              having to browse (and do something similar on sale orders). """
        res = super()._l10n_br_build_avatax_line(product, qty, unit_price, total, discount, line_id)

        # Transform the descriptions of the lines to something Avatax will trim correctly.
        name = self.env["account.move.line"].browse(line_id).name
        res["itemDescriptor"]["description"] = name and name.replace("\n", " | ")
        return res
