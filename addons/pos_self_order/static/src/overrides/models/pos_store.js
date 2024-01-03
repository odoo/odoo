/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async processServerData(loadedData) {
        await super.processServerData(...arguments);
        this.self_ordering = this.data.custom.self_ordering;
    },
    async getServerOrders() {
        if (this.self_ordering) {
            await this.data.callRelated("pos.order", "get_standalone_self_order", []);
        }

        return await super.getServerOrders(...arguments);
    },
});
