import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async onDeleteOrder(order) {
        if (order.config.is_history_tracked) {
            this.addPendingOrder([order.id]);
            // Save order to server.
            await this.syncAllOrders({ throw: true, orders: [order] });
        }
        return await super.onDeleteOrder(...arguments);
    },
});
