import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    //@Override
    async _finalizeValidation() {
        await super._finalizeValidation(...arguments);
        const order = this.currentOrder;
        // note: isSACompany guarantees order.is_to_invoice()
        // Skip if invoice is not mandatory(Ex: settlement)
        // note: Skips entirely if journal is not onboarded or electronic invoicing is not selected
        if (
            order.finalized &&
            !order.l10n_sa_invoice_qr_code_str &&
            order.isInvoiceMandatoryForSA()
        ) {
            const orderError = _t("%s by going to Backend > Orders > Invoice", order.pos_reference);
            const href = `/odoo/customer-invoices/${this.currentOrder?.raw?.account_move}`;
            const link = markup`<a target="_blank" href=${href} class="text-info fw-bolder">${_t(
                "Invoice"
            )}</a>`;
            const errorInfo = this.currentOrder.raw.account_move ? link : orderError;
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
    },

    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        // the isSettleDueLine() is only available if enterprise:pos_settle_due module is installed
        const settleLineCount = order.lines.filter((line) => line.isSettleDueLine?.()).length;
        if (settleLineCount && settleLineCount !== order.lines.length) {
            return this.dialog.add(AlertDialog, {
                title: _t("Settlement Error"),
                body: _t(
                    "Please remove the new order lines from the order to proceed with the settlement."
                ),
            });
        }
        await super.validateOrder(...arguments);
    },
});
