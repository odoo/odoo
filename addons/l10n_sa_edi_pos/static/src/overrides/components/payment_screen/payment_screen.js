import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    //@Override
    async _finalizeValidation() {
        await super._finalizeValidation(...arguments);
        const order = this.currentOrder;
        // note: isSACompany guarantees order.is_to_invoice()
        if (order.isSACompany && order.finalized && order.l10n_sa_invoice_edi_state !== "sent") {
            const orderError = `${order.pos_reference} by going to Backend > Orders > Invoice`;
            const link = markup(
                `<a target="_blank" href="/odoo/customer-invoices/${this.currentOrder.raw.account_move}" class="text-info fw-bolder">Invoice</a>`
            );
            const errorInfo = this.currentOrder.raw.account_move ? link : orderError;
            const message =
                `The Receipt and Invoice generated here are not valid documents as there is ` +
                `an error in their processing. You need to resolve the errors first in %s` +
                `. Upon Successful submission, you can reprint the Invoice and the Receipt.`;

            this.dialog.add(ConfirmationDialog, {
                title: _t("ZATCA Validation Error"),
                body: _t(message, errorInfo),
            });
        }
    },
});
