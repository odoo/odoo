/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setTable(table, orderUid = null) {
        await super.setTable(...arguments);
        this.selectedOrder._updateRewards();
    },
});
