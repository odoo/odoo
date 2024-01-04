/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosBus } from "@point_of_sale/app/bus/pos_bus_service";

patch(PosBus.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        this.busService.subscribe("ONLINE_PAYMENTS_NOTIFICATION", (payload) => {
            // The bus communication is only protected by the name of the channel.
            // Therefore, no sensitive information is sent through it, only a
            // notification to invite the local browser to do a safe RPC to
            // the server to check the new state of the order.
            const currentOrder = this.pos.get_order();
            if (currentOrder && currentOrder.server_id === payload.id) {
                currentOrder.update_online_payments_data_with_server(false);
            }
        });
    },
});
