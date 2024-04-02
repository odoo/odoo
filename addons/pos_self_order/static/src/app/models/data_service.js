/** @odoo-module */

import { PosData } from "@point_of_sale/app/models/data_service";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

patch(PosData.prototype, {
    async fetchData() {
        const configId = odoo.pos_config_id;
        const accessToken = odoo.access_token;
        const response = await rpc("/pos-self-order/load_data", {
            config_id: configId,
            access_token: accessToken,
        });
        return response;
    },
    initIndexedDB() {
        return;
    },
    loadIndexedDBData() {
        return;
    },
    syncDataWithIndexedDB() {
        return;
    },
});
