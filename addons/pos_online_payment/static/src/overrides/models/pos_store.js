/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("ONLINE_PAYMENTS_NOTIFICATION", ({ id, extra_data }) => {
            // The bus communication is only protected by the name of the channel.
            // Therefore, no sensitive information is sent through it, only a
            // notification to invite the local browser to do a safe RPC to
            // the server to check the new state of the order.
            const currentOrder = this.get_order();
            if (currentOrder && currentOrder.server_id === id) {
                (async () => {
                    if (extra_data) {
                        await currentOrder.updateWithServerData({
                            "extra_data": extra_data
                        });
                    }
                })().then(() => {
                    currentOrder.update_online_payments_data_with_server(false);
                });
            }
        });
    },
});
