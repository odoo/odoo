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

    async _onBeforeDeleteOrder(order) {
        if (order.payment_ids.some((line) => line.isBancontactRefundPending)) {
            this.notification.add(
                _t(
                    "The order %s has a pending refund: check its status or force it done before deleting the order.",
                    order.floatingOrderName
                ),
                { type: "warning" }
            );
            return false;
        }
        return super._onBeforeDeleteOrder(...arguments);
    },

    async handleBancontactPayNotification({ bancontact_id, bancontact_status }) {
        const paymentline = this.models["pos.payment"].find(
            (line) => line.bancontact_id === bancontact_id
        );
        if (!paymentline || paymentline.isDone()) {
            return;
        }

        const order = paymentline.pos_order_id;
        if (!order || order.finalized) {
            return;
        }

        const currentOrder = this.getOrder();

        // --- SUCCEEDED ---
        if (bancontact_status === "SUCCEEDED") {
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

    async handleBancontactRefundStatus(line, { fromPolling = false } = {}) {
        const order = line.pos_order_id;
        if (!order || order.finalized) {
            return;
        }
        const isCurrentOrder = order === this.getOrder();

        if (line.payment_status === "done") {
            if (!isCurrentOrder) {
                this.notification.add(
                    _t("The refund for order %s has been completed.", order.floatingOrderName),
                    { type: "success" }
                );
                return;
            }
            await this.autoValidateOrder({ order });
        } else if (!line.payment_status) {
            const message = isCurrentOrder
                ? _t("The refund failed.")
                : _t("A refund for order %s has failed.", order.floatingOrderName);
            this.notification.add(message, { type: "danger" });
        } else if (fromPolling) {
            const message = isCurrentOrder
                ? _t("The refund is still pending. Check its status later or force it done.")
                : _t(
                      "The refund for order %s is still pending. Check its status later or force it done.",
                      order.floatingOrderName
                  );
            this.notification.add(message, { type: "warning" });
        } else {
            this.notification.add(_t("The refund is still pending."), { type: "info" });
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
