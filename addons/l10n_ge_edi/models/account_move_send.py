from odoo import api, models

from odoo.addons.l10n_ge_edi.tools.rsge_client import (
    RSGE_TRANSIENT_ERROR_KINDS,
    translate_rsge_error,
)


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({"ge_edi": {"label": self.env._("to RS.ge"), "is_applicable": self._is_ge_edi_applicable}})
        return res

    @api.model
    def _is_ge_edi_applicable(self, move):
        return (
            move.l10n_ge_edi_state in {"not_sent", "error", "new_correction", "rejected_correction", "rejected"}
            and move.is_invoice(include_receipts=True)
            and move.country_code == "GE"
        )

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        ge_edi_moves = moves.filtered(lambda m: "ge_edi" in moves_data[m]["extra_edis"])
        if not ge_edi_moves:
            return alerts

        if sellers_missing_un_id := ge_edi_moves.company_id.partner_id.filtered(lambda p: not p.l10n_ge_edi_un_id):
            alerts["ge_edi_seller_missing_un_id"] = {
                "level": "danger",
                "message": self.env._("Fetch the RS.ge Un Id on your company's partner before sending."),
                "action_text": self.env._("View Partner(s)"),
                "action": sellers_missing_un_id._get_records_action(name=self.env._("Check RS.ge Un Id")),
            }

        if buyers_missing_un_id := ge_edi_moves.partner_id.filtered(lambda p: not p.l10n_ge_edi_un_id):
            alerts["ge_edi_buyer_missing_un_id"] = {
                "level": "danger",
                "message": self.env._("Fetch the RS.ge Un Id on the customer before sending."),
                "action_text": self.env._("View Partner(s)"),
                "action": buyers_missing_un_id._get_records_action(name=self.env._("Check RS.ge Un Id")),
            }
        return alerts

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            if "ge_edi" not in invoice_data["extra_edis"]:
                continue
            if error := invoice._l10n_ge_edi_submit_invoice():
                invoice_data["error"] = {
                    "error_title": self.env._("Error when sending the invoice to RS.ge:"),
                    "errors": [translate_rsge_error(self.env, error)],
                    "retry": error.kind in RSGE_TRANSIENT_ERROR_KINDS,
                }
            # keep the RS.ge ids written so far, or the rollback on error re-registers the invoice
            if self._can_commit():
                self.env.cr.commit()
