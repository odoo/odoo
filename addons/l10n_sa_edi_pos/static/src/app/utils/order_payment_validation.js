import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { markup } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(OrderPaymentValidation.prototype, {
    setup(vals) {
        super.setup(...arguments);
        this.dialog = this.pos.env.services.dialog;
    },
    async finalizeValidation() {
        const potentialValidationError = await super.finalizeValidation(...arguments);

        // note: isSACompany guarantees order.is_to_invoice()
        // expect for cases like deposit and settlement
        // Skip if invoice is not mandatory(Ex: settlement)
        // Skips entirely if journal is not onboarded or electronic invoicing is not selected
        if (
            this.order.isInvoiceMandatoryForSA() &&
            this.order.finalized &&
            !this.order.l10n_sa_invoice_qr_code_str
        ) {
            const orderError = _t(
                "%s by going to Backend > Orders > Invoice",
                this.order.pos_reference
            );
            const href = `/odoo/customer-invoices/${this.order?.raw?.account_move}`;
            const link = markup`<a target="_blank" href=${href} class="text-info fw-bolder">${_t(
                "Invoice"
            )}</a>`;
            const errorInfo = this.order.raw.account_move ? link : orderError;
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
        return potentialValidationError;
    },
});
