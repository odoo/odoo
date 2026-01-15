import { RestaurantTable } from "@pos_restaurant/app/models/restaurant_table";
import { patch } from "@web/core/utils/patch";

patch(RestaurantTable.prototype, {
    get useProxy() {
        return super.useProxy || (this.iot_device_ids && this.iot_device_ids.length > 0);
    },
    get isShareable() {
        return super.isShareable || this.module_pos_restaurant;
    },
    getOrders() {
        const orders = super.getOrders();
        const selfOrdering = this.models["pos.order"].filter(
            (o) =>
                o.self_ordering_table_id?.id === this.id &&
                o.table_id?.id !== this.id &&
                (!o.finalized || o.uiState.screen_data?.value?.name === "TipScreen")
        );
        return [...orders, ...selfOrdering];
    },
});
