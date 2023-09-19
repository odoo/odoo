/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";

patch(OrderWidget.prototype, {
    get buttonToShow() {
        const type = this.selfOrder.config.self_ordering_mode;
        const mode = this.selfOrder.config.self_ordering_pay_after;
        const isOnlinePayment = this.selfOrder.pos_payment_methods.find((p) => p.is_online_payment);

        if (type === "kiosk") {
            return super.buttonToShow;
        }

        if (mode === "each") {
            return { label: _t("Pay"), disabled: false };
        } else if (mode === "meal") {
            const order = this.selfOrder.currentOrder;

            if (!order) {
                return { label: "", disabled: true };
            }

            if (!order.isSavedOnServer) {
                return { label: _t("Order"), disabled: false };
            } else {
                if (isOnlinePayment) {
                    return { label: _t("Pay"), disabled: false };
                } else {
                    return { label: _t("Pay at cashier"), disabled: true };
                }
            }
        } else {
            return super.buttonToShow;
        }
    },
});
