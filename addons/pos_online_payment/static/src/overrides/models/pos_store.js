/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("ONLINE_PAYMENTS_NOTIFICATION", ({ id }) => {
            // The bus communication is only protected by the name of the channel.
            // Therefore, no sensitive information is sent through it, only a
            // notification to invite the local browser to do a safe RPC to
            // the server to check the new state of the order.
            if (this.get_order()?.server_id === id) {
                this.get_order().update_online_payments_data_with_server(this.orm, false);
            }
        });
    },
});
