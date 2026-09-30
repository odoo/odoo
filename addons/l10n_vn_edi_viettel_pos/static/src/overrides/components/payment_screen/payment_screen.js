/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";

patch(PaymentScreen.prototype, {
    onMounted() {
        super.onMounted(...arguments);
        // The base onMounted auto-enables invoice for refund orders when the original
        // order was invoiced. We need to reset it here so the
        // user will manually enable it and provide a reason.
        if (this.pos.isVietnamCompany() && this.currentOrder.isRefund) {
            this.currentOrder.setToInvoice(false);
        }
    },
    async toggleIsToInvoice() {
        if (
            this.pos.isVietnamCompany() &&
            this.pos.config.l10n_vn_auto_send_to_sinvoice &&
            !this.currentOrder.to_invoice &&
            this.currentOrder.lines.some((line) => line.refunded_orderline_id) // Refund Order
        ) {
            const reason = await makeAwaitable(this.dialog, TextInputPopup, {
                rows: 4,
                title: _t("Refund Reason"),
            });
            if (reason) {
                this.currentOrder.l10n_vn_credit_note_reason = reason;
            }
        }
        super.toggleIsToInvoice(...arguments);
    },
});
