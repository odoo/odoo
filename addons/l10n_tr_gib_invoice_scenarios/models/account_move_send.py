from collections import defaultdict

from odoo import _, models
from odoo.tools.float_utils import float_compare


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        # Add the Nilvera PDF to the mail attachments for answered commercial documents.
        attachments = super()._get_invoice_extra_attachments(move)
        if (
            move.l10n_tr_nilvera_send_status
            in {"commercial_approved", "commercial_rejected", "commercial_answered_automatically"}
            and move.message_main_attachment_id.id != move.invoice_pdf_report_id.id
        ):
            attachments += move.message_main_attachment_id
        return attachments

    def _get_alerts(self, moves, moves_data):
        # EXTENDS l10n_tr_nilvera_einvoice
        alerts = super()._get_alerts(moves, moves_data)

        # Filter for moves that have 'tr_nilvera' in their EDI data
        tr_nilvera_moves = moves.filtered(lambda m: "tr_nilvera" in moves_data[m]["extra_edis"])

        if invalid_invoice_references := tr_nilvera_moves._l10n_tr_nilvera_einvoice_check_invalid_invoice_reference():
            alerts["tr_moves_with_invalid_invoice_reference"] = {
                "level": "danger",
                "message": _("The credit notes must have a valid reference to the original invoice in the reference field"),
                "action_text": _("Check reference on Invoice(s)"),
                "action": invalid_invoice_references._get_records_action(name=_("Check reference on Credit Note(s)")),
            }

        if invalid_type_invoices := tr_nilvera_moves.filtered(
            lambda r: (r.l10n_tr_gib_invoice_type in {"IADE", "TEVKIFATIADE"}) ^ (r.move_type == "out_refund")
        ):
            alerts["tr_moves_with_invalid_type"] = {
                "level": "danger",
                "message": _("Type 'Return' and 'Withholding Return' should only be used for Credit Notes"),
                "action_text": _("Check invoice type"),
                "action": invalid_type_invoices._get_records_action(name=_("Check Invoice Type")),
            }

        if tr_withholding_credit_note_tax_mismatch := self._l10n_tr_withholding_credit_note_tax_mismatch(tr_nilvera_moves):
            alerts["tr_withholding_credite_note_tax_mismatch"] = tr_withholding_credit_note_tax_mismatch

        if tr_credit_note_invoice_not_sent := tr_nilvera_moves.filtered(
            lambda r: (
                r.move_type == "out_refund"
                and r.reversed_entry_id
                and r.reversed_entry_id.l10n_tr_nilvera_send_status not in {"sent", "waiting", "succeed"}
            )
        ):
            alerts["tr_credit_note_invoice_not_sent"] = {
                "level": "danger",
                "message": _(
                    "Return invoices can only be sent if the original invoice has already been successfully sent to Nilvera"
                ),
                "action_text": _("View Invoice(s)"),
                "action": tr_credit_note_invoice_not_sent.reversed_entry_id._get_records_action(name=_("View Invoice(s)")),
            }
        return alerts

    def _l10n_tr_withholding_credit_note_tax_mismatch(self, moves):
        errors = defaultdict(defaultdict)
        for invoice in moves.filtered(
            lambda r: r.country_code == "TR" and r.move_type == "out_refund" and r.l10n_tr_gib_invoice_type == "TEVKIFATIADE"
        ):
            for line in invoice.invoice_line_ids:
                tax_amount = line.price_total - line.price_subtotal
                expected_percentage = (line.l10n_tr_original_quantity and line.quantity / line.l10n_tr_original_quantity) or 0
                expected_tax_amount = expected_percentage * line.l10n_tr_original_tax_without_withholding
                if float_compare(tax_amount, expected_tax_amount, line.currency_id.decimal_places) != 0:
                    errors[invoice.name][line.product_id.name] = (
                        f"{line.currency_id.format(tax_amount)} != {line.currency_id.format(expected_tax_amount)}"
                    )

        if not errors:
            return ""

        error_message = _(
            "For withholding return invoices, the tax amount is expected to be the same percentage as the returned quantity.\n"
            "The following mismatch was found:\n"
        )
        for invoice, lines in errors.items():
            for line, error in lines.items():
                error_message += "- [%s] - %s: %s\n" % (invoice, line, error)

        error_message += _("Make sure the price and taxes match the original invoice.")
        return {
            "level": "danger",
            "message": error_message,
            "action_text": _("Check Tax Amounts on Credit Note(s)"),
            "action": moves._get_records_action(name=_("Check Tax Amounts on Credit Note(s)")),
        }
