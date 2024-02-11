/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const data = super.getReceiptHeaderData(...arguments);
        data.delivery = this.getDeliveryData(order);
        return data;
    },
    getDeliveryData(order) {
        return {
            provider_name: order.delivery_provider_name,
            note: order.delivery_note,
            date_order: new Date(order.date_order).toLocaleString(),
        };
    },
    async processServerData() {
        super.processServerData(...arguments);
        this.delivery_order_count = this.data.custom.delivery_order_count;
    },
});
