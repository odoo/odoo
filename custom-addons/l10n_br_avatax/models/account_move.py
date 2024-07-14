# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_br_get_operation_type(self):
        """account.external.tax.mixin override."""
        if self.debit_origin_id:
            return "amountComplementary"
        elif self.move_type == "out_refund":
            return "salesReturn"

        return super()._l10n_br_get_operation_type()

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
            return self._l10n_br_invoice_refs_for_code("documentCode", f"account.move_{origin.id}")

        return {}
