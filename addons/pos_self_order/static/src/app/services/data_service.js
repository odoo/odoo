import { PosData } from "@point_of_sale/app/services/data_service";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

patch(PosData.prototype, {
    async loadInitialData() {
        const configId = session.data.config_id;
        return await rpc(`/pos-self/data/${parseInt(configId)}`);
    },
    async loadFieldsAndRelations() {
        const configId = session.data.config_id;
        return await rpc(`/pos-self/relations/${parseInt(configId)}`);
    },
    get databaseName() {
        return `pos-self-order-${odoo.pos_config_id}-${odoo.info?.db}`;
    },
    initIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? super.initIndexedDB(...arguments)
            : true;
    },
    async flush() {
        this.queue = [];
    },
    async missingRecursive(recordMap) {
        return recordMap;
    },
});
