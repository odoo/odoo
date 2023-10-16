/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { _t } from "@web/core/l10n/translation";

patch(CartPage.prototype, {
    async pay() {
        const isOnlinePayment = this.selfOrder.pos_payment_methods.find((p) => p.is_online_payment);

        if (!isOnlinePayment) {
            return super.pay(...arguments);
        }

        if (this.sendInProgress) {
            return;
        }

        const order = this.selfOrder.currentOrder;
        const mode = this.selfOrder.config.self_ordering_pay_after;
        const service = this.selfOrder.config.self_ordering_service_mode;
        const takeAway = this.selfOrder.currentOrder.take_away;

        if (!this.selfOrder.table && service === "table" && !takeAway) {
            this.state.selectTable = true;
            return;
        }

        if (mode === "meal" && order.isSavedOnServer) {
            this.checkAndOpenPaymentPage(order);
        } else if (mode === "meal" && !order.isSavedOnServer) {
            this.sendInProgress = true;
            await this.selfOrder.sendDraftOrderToServer();

            this.router.navigate("confirmation", {
                orderAccessToken: order.access_token,
                screenMode: "order",
            });
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
                    // if no payment method is available -> pay at cashier
                    this.router.navigate("confirmation", {
                        orderAccessToken: order.access_token,
                        screenMode: "pay",
                    });
                    return;
                }

                if (
                    !order.isSavedOnServer &&
                    this.selfOrder.config.self_ordering_mode !== "kiosk"
                ) {
                    await this.selfOrder.sendDraftOrderToServer();
                }

                if (this.selfOrder.config.self_ordering_mode === "mobile") {
                    const onlinePaymentUrl = this.selfOrder.getOnlinePaymentUrl(order, true);
                    window.open(onlinePaymentUrl, "_self");
                } else {
                    this.router.navigate("payment");
                }
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
