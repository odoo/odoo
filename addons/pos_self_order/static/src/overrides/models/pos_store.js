/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async processServerData(loadedData) {
        await super.processServerData(...arguments);
    },
    async getServerOrders() {
        if (this.session._self_ordering) {
            await this.data.callRelated("pos.order", "get_standalone_self_order", []);
        }

        return await super.getServerOrders(...arguments);
    },
});
