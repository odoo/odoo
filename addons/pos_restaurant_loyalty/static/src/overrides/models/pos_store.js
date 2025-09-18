/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";

import { patch } from "@web/core/utils/patch";
patch(PosStore.prototype, {
    // @Override
    async setTable(table, orderUid = null) {
        await super.setTable(...arguments);
        await this.updateRewards();
    },
});
