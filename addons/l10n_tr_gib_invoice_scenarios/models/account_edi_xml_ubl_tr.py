from odoo import models
from odoo.exceptions import UserError


class AccountEdiXmlUblTr(models.AbstractModel):
    _inherit = "account.edi.xml.ubl.tr"

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        # EXTENDS account.edi.xml.ubl_20
        logs = super()._import_fill_invoice(invoice, tree, qty_factor)

        scenario = self._find_value(".//cbc:ProfileID", tree)
        if scenario not in {key for key, _ in self.env["account.move"]._fields["l10n_tr_gib_invoice_scenario"].selection}:
            scenario = False
        invoice_type = self._find_value(".//cbc:InvoiceTypeCode", tree)
        if invoice_type not in {key for key, _ in self.env["account.move"]._fields["l10n_tr_gib_invoice_type"].selection}:
            invoice_type = False

        invoice.write(
            {
                "l10n_tr_gib_invoice_scenario": scenario,
                "l10n_tr_gib_invoice_type": invoice_type,
            }
        )

        if scenario == "TICARIFATURA" and invoice.move_type in {"in_invoice", "out_invoice"}:
            try:
                # Don't want to block the import in case status retrieval fails
                invoice.l10n_tr_action_fetch_ticarifatura_response()
            except UserError as e:
                logs.append(self.env._("Failed to fetch TICARIFATURA response: %s", str(e)))

        return logs
