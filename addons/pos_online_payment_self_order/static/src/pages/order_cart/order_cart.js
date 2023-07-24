/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { OrderCart } from "@pos_self_order/mobile/pages/order_cart/order_cart";
import { _t } from "@web/core/l10n/translation";

patch(OrderCart.prototype, {
    get buttonToShow() {
        if (this.selfOrder.self_order_mode === "each") {
            return { label: _t("Pay"), disabled: false };
        } else if (this.selfOrder.self_order_mode === "meal") {
            const order = this.selfOrder.currentOrder;
            if (!order) {
                return { label: "", disabled: true };
            }
            if (!order.isSavedOnServer) {
                return { label: _t("Order"), disabled: false };
            } else {
                if (this.selfOrder.has_self_order_online_payment_method) {
                    return { label: _t("Pay"), disabled: false };
                } else {
                    return { label: _t("Pay at cashier"), disabled: true };
                }
            }
        } else {
            return super.buttonToShow;
        }
    },
    async processOrder() {
        if (this.sendInProgress) {
            return;
        }

        if (!this.selfOrder.table) {
            this.state.selectTable = true;
            return;
        }

        if (this.selfOrder.self_order_mode === "meal" && this.selfOrder.has_self_order_online_payment_method) {
            const order = this.selfOrder.currentOrder;
            if (!order) {
                this.selfOrder.notification.add(_t("The current order is invalid."), { type: "danger" });
                return;
            }
            if (!order.isSavedOnServer) {
                this.sendInProgress = true;
                await this.selfOrder.sendDraftOrderToServer();
                this.sendInProgress = false;
            } else {
                this.checkAndOpenPaymentPage(order);
            }
        } else if (this.selfOrder.self_order_mode === "each") {
            this.sendInProgress = true;
            const order = await this.selfOrder.sendDraftOrderToServer();
            this.sendInProgress = false;
            this.checkAndOpenPaymentPage(order);
        } else {
            return super.processOrder(...arguments);
        }
    },
    checkAndOpenPaymentPage(order) {
        if (order) {
            if (order.state === "draft") {
                this.selfOrder.openOnlinePaymentPage(order);
            } else {
                this.selfOrder.notification.add(_t("The current order cannot be paid (maybe it is already paid)."), { type: "danger" });
            }
        } else {
            this.selfOrder.notification.add(_t("The order could not be saved, therefore its payment is unavailable."), { type: "danger" });
        }
    },
});
