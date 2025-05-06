import { PosData } from "@point_of_sale/app/models/data_service";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

patch(PosData.prototype, {
    async setup() {
        await super.setup(...arguments);

        // Override Point of Sale deviceSync object to avoid errors
        this.deviceSync = {
            dispatch: () => void 0,
        };
    },
    async loadInitialData() {
        const configId = session.data.config_id;
        return await rpc(`/pos-self/data/${parseInt(configId)}`);
    },
    get databaseName() {
        return `self_order-${odoo.access_token}`;
    },
    initIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? super.initIndexedDB(...arguments)
            : true;
    },
    deleteDataIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? super.deleteDataIndexedDB(...arguments)
            : true;
    },
    syncDataWithIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? super.syncDataWithIndexedDB(...arguments)
            : true;
    },
    async loadIndexedDBData() {
        return session.data.self_ordering_mode === "mobile"
            ? await super.loadIndexedDBData(...arguments)
            : {};
    },
    async missingRecursive(recordMap) {
        return recordMap;
    },
});
