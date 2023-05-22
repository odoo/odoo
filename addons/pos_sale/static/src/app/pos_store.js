/** @odoo-module */

import { PosStore } from "@point_of_sale/app/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, "pos_sale.PosStore", {
    setup(...args) {
        this.orderManagement = { searchString: "", selectedOrder: null };
        return this._super(...args);
    },
});
