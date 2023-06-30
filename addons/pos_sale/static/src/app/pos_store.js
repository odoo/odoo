/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, "pos_sale.PosStore", {
    async setup(...args) {
        this.orderManagement = { searchString: "", selectedOrder: null };
        return await this._super(...args);
    },
});
