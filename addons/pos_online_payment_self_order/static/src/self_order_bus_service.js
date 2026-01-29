/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { SelfOrderBus } from "@pos_self_order/app/self_order_bus_service";

patch(SelfOrderBus.prototype, {
    dispatch(message) {
        super.dispatch(...arguments);

        if (message.type === "ONLINE_PAYMENT_STATUS") {
            this.ws_changeOnlinePaymentStatus(message.payload.status, message.payload.order);
        }
    },
    ws_changeOnlinePaymentStatus(status, order) {
        const currentOrder = this.selfOrder.currentOrder;
        this.selfOrder.onlinePaymentStatus = status;
        this.selfOrder.paymentError = status === "fail";

        if (status === "success" && currentOrder.access_token === order.access_token) {
            this.selfOrder.finalizeOrder();
        }
    },
});
