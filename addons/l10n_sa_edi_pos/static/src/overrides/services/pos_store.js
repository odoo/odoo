import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { markup } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    _handleInvoiceNotification(order, error) {
        // note: isSACompany guarantees order.is_to_invoice()
        // expect for cases like deposit and settlement
        // Skip if invoice is not mandatory(Ex: settlement)
        // Skips entirely if journal is not onboarded or electronic invoicing is not selected
        if (
            order.isInvoiceMandatoryForSA() &&
            order.finalized &&
            !order.l10n_sa_invoice_qr_code_str
        ) {
            const orderError = _t("%s by going to Backend > Orders > Invoice", order.pos_reference);
            const href = `/odoo/customer-invoices/${order?.raw?.account_move}`;
            const link = markup`<a target="_blank" href=${href} class="text-info fw-bolder">${_t(
                "Invoice"
            )}</a>`;
            const errorInfo = order.raw.account_move ? link : orderError;
            const message = _t(
                `The Receipt and Invoice generated here are not valid documents as there is ` +
                    `an error in their processing. You need to resolve the errors first in %s` +
                    `. Upon Successful submission, you can reprint the Invoice and the Receipt.`,
                errorInfo
            );

            this.dialog.add(ConfirmationDialog, {
                title: _t("ZATCA Validation Error"),
                body: message,
            });
        }
        return super._handleInvoiceNotification(order, error);
    },
});
