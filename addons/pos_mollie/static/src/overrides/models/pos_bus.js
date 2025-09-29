/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    // Override
    dispatch(message) {
        super.dispatch(...arguments);

        if (message.type === "MOLLIE_STATUS_UPDATE" && message.payload.config_id === this.pos.config.id) {
            this.pos
                .getPendingPaymentLine("mollie")
                .payment_method.payment_terminal.handleMollieStatusResponse(message.payload);
        }
    },
});
