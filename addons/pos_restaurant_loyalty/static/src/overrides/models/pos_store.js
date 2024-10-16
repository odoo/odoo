/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    // @Override
    async setTable(table, orderUid = null) {
        await super.setTable(...arguments);
        await this.updateRewards();
    },
});
