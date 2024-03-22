/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup(...args) {
        this.orderManagement = { searchString: "", selectedOrder: null };
        return await super.setup(...args);
    },
    selectOrderLine(order, line) {
        super.selectOrderLine(...arguments);
        if (
            line &&
            this.config.down_payment_product_id &&
            line.product_id.id === this.config.down_payment_product_id.id
        ) {
            this.numpadMode = "price";
        }
    },
});
