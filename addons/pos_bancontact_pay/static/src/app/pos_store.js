import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.handleBancontactPayNotification = this.handleBancontactPayNotification.bind(this);
        this.data.connectWebSocket(
            "BANCONTACT_PAY_PAYMENTS_NOTIFICATION",
            this.handleBancontactPayNotification
        );
    },

    async handleBancontactPayNotification({ bancontact_id, bancontact_status }) {
        const paymentline = this.models["pos.payment"].find(
            (line) => line.bancontact_id === bancontact_id
        );
        if (!paymentline || paymentline.payment_status === "done") {
            return;
        }

        const order = paymentline.pos_order_id;
        if (!order || order.finalized) {
            return;
        }

        const currentOrder = this.getOrder();

        // --- SUCCEEDED ---
        if (bancontact_status === "SUCCEEDED") {
            paymentline.updateCustomerDisplayQrCode(null);
            paymentline.setPaymentStatus("done");
            paymentline.qr_code = null;

            // Other order selected
            if (order !== currentOrder) {
                const message = order.toBeValidate()
                    ? `The order ${order.floatingOrderName} has been fully paid.\nYou just need to validate it.`
                    : `The order ${order.floatingOrderName} has been partially paid.`;
                this.notification.add(message, { type: "success" });
                return;
            }

            // Close QR code if currently displayed
            if (paymentline.uuid === this.qrCode?.paymentline.uuid) {
                this.closeQrCode();
            }

            // Notify only if another payment line is selected
            if (paymentline.uuid !== currentOrder.getSelectedPaymentline()?.uuid) {
                this.notification.add(_t("Payment received"), { type: "success" });
            }
            await this.autoValidateOrder({ order });
            return;
        }

        // --- FAILED ---
        if (
            paymentline.payment_status !== "retry" &&
            ["AUTHORIZATION_FAILED", "FAILED", "EXPIRED", "CANCELLED"].includes(bancontact_status)
        ) {
            paymentline.updateCustomerDisplayQrCode(null);
            paymentline.setPaymentStatus("retry");
            paymentline.bancontact_id = null;
            paymentline.qr_code = null;

            const message = this.getBancontactErrorMessage(bancontact_status, order);
            this.notification.add(message, { type: "warning" });

            // Close QR code if currently displayed
            if (paymentline.uuid === this.qrCode?.paymentline.uuid) {
                this.closeQrCode();
            }

            return;
        }
    },

    getBancontactErrorMessage(status, order) {
        const isCurrentOrder = order === this.getOrder();
        if (status === "EXPIRED") {
            return isCurrentOrder
                ? _t("Payment expired")
                : _t("A payment for order %s has expired.", order.floatingOrderName);
        }
        if (status === "CANCELLED") {
            return isCurrentOrder
                ? _t("Payment cancelled")
                : _t("A payment for order %s was cancelled.", order.floatingOrderName);
        }
        return isCurrentOrder
            ? _t("Payment failed")
            : _t("A payment for order %s has failed.", order.floatingOrderName);
    },
});
