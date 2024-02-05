/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.bus.subscribe("DELIVERY_ORDER_COUNT", (payload) => {
            if (this.config.raw.delivery_service_ids) {
                this.ws_syncDeliveryCount(payload);
            }
        });
    },
    async _fetchDeliverooOrderCount() {
        this.delivery_order_count.deliveroo = await this.data.call(
            "pos.config",
            "get_deliveroo_order_count",
            [this.config.id],
            {}
        );
    },
    getDeliveryData(order) {
        const res = super.getDeliveryData(...arguments);
        res["display"] = order.delivery_display;
        res["prepare_for"] = new Date(order.delivery_prepare_for).toLocaleString();
        res["start_preparing_at"] = new Date(order.delivery_start_preparing_at).toLocaleString();
        res["confirm_at"] = new Date(order.delivery_confirm_at).toLocaleString();
        return res;
    },
    ws_syncDeliveryCount(data) {
        this.delivery_order_count = data;
    },
});

patch(Order.prototype, {
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.delivery_display = json.delivery_display;
        this.delivery_prepare_for = json.delivery_prepare_for;
    },
});
