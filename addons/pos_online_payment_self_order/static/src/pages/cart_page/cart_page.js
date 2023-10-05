/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { _t } from "@web/core/l10n/translation";

patch(CartPage.prototype, {
    async pay() {
        if (this.selfOrder.config.self_ordering_mode === "kiosk") {
            return super.pay(...arguments);
        }

        if (this.sendInProgress) {
            return;
        }

        const order = this.selfOrder.currentOrder;
        const mode = this.selfOrder.config.self_ordering_pay_after;
        const isOnlinePayment = this.selfOrder.pos_payment_methods.find((p) => p.is_online_payment);
        const service = this.selfOrder.config.self_ordering_service_mode;
        const takeAway = this.selfOrder.currentOrder.take_away;

        if (!this.selfOrder.table && service === "table" && !takeAway) {
            this.state.selectTable = true;
            return;
        }

        if (mode === "meal" && isOnlinePayment) {
            if (!order) {
                this.selfOrder.notification.add(_t("The current order is invalid."), {
                    type: "danger",
                });
                return;
            }
            if (!order.isSavedOnServer) {
                this.sendInProgress = true;
                await this.selfOrder.sendDraftOrderToServer();
                this.sendInProgress = false;
            } else {
                this.checkAndOpenPaymentPage(order);
            }
        } else if (mode === "each") {
            this.checkAndOpenPaymentPage(order);
        } else {
            return super.pay(...arguments);
        }
    },
    async checkAndOpenPaymentPage(order) {
        const isOnlinePayment = this.selfOrder.pos_payment_methods.find((p) => p.is_online_payment);

        if (order) {
            if (order.state === "draft") {
                if (!isOnlinePayment) {
                    this.selfOrder.notification.add(
                        _t("The current order cannot be paid (no online payment method)."),
                        { type: "danger" }
                    );
                    return;
                }

                if (!order.isSavedOnServer) {
                    await this.selfOrder.sendDraftOrderToServer();
                }

                this.selfOrder.openOnlinePaymentPage(order);
            } else {
                this.selfOrder.notification.add(
                    _t("The current order cannot be paid (maybe it is already paid)."),
                    { type: "danger" }
                );
            }
        } else {
            this.selfOrder.notification.add(
                _t("The order could not be saved, therefore its payment is unavailable."),
                { type: "danger" }
            );
        }
    },
});
