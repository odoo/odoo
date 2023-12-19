/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    // Override
    setup() {
        super.setup(...arguments);

        if (this.pos.config.delivery_service_id) {
            this.initTableOrderCount();
        }
    },
    // Override
    dispatch(message) {
        super.dispatch(...arguments);

        if (message.type === "DELIVEROO_ORDER_COUNT") {
            this.ws_syncDeliverooCount(message.payload);
        }
    },
    ws_syncDeliverooCount(data) {
        this.pos.delivery_order_count.deliveroo = data;
    },
});
