/** @odoo-module */

import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";
import { patch } from "@web/core/utils/patch";

patch(PosBus.prototype, {
    // Override
    dispatch(message) {
        super.dispatch(...arguments);

        if (message.type === "ALIPAY_LATEST_RESPONSE" && message.payload === this.pos.config.id) {
            this.pos
                .getPendingPaymentLine("alipay")
                .payment_method.payment_terminal.alipayHandleNotification();
        }
    },
});
