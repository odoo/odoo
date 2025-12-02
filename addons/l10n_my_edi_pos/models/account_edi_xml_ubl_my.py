# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountEdiXmlUBLMyInvoisMY(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_myinvois_my"

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _add_myinvois_document_monetary_total_vals(self, vals):
        super()._add_myinvois_document_monetary_total_vals(vals)

        myinvois_document = vals["myinvois_document"]
        if myinvois_document.pos_order_ids:
            # Add the total amount paid.
            vals.update({
                'total_paid_amount': sum(order.amount_paid / order.currency_rate for order in myinvois_document.pos_order_ids),
                'total_paid_amount_currency': sum(myinvois_document.pos_order_ids.mapped('amount_paid')),
            })

    @api.model
    def _l10n_my_edi_get_refund_details(self, invoice):
        """
        Override in order to get the original document from the PoS order in case of refund of a
        PoS consolidated invoice.

        Note that by design, we consider that a refund done in a PoS is an actual refund and never a
        credit note.
        :param invoice: The credit note for which we want to get the refunded document.
        :return: A tuple, where the first parameter indicates if this credit note is a refund and the second the credited/refunded document.
        """
        if not invoice.pos_order_ids:
            return super()._l10n_my_edi_get_refund_details(invoice)  # the existing logic is enough.

        refunded_order = invoice.pos_order_ids[0].refunded_order_id
        consolidated_invoices = refunded_order._get_active_consolidated_invoice()
        return True, consolidated_invoices
