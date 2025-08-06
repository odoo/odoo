import { PosData } from "@point_of_sale/app/services/data_service";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

patch(PosData.prototype, {
    async loadInitialData() {
        const configId = session.data.config_id;
        const data = await rpc(`/pos-self/data/${parseInt(configId)}`);
        const params = this.getFieldsAndRelations(data);
        await this.initIndexedDB(params);
        const localData = await this.getCachedServerDataFromIndexedDB();
        this.initFieldsAndRelations(params);
        await this.syncInitialData(data, localData, {});
        return Object.fromEntries(Object.entries(data).map(([key, value]) => [key, value.records]));
    },
    async loadFieldsAndRelations() {
        // Deprecated
        // Kept for backward compatibility
        const configId = session.data.config_id;
        return await rpc(`/pos-self/relations/${parseInt(configId)}`);
    },
    get databaseName() {
        return `self_order-${odoo.access_token}`;
    },
    initIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? super.initIndexedDB(...arguments)
            : true;
    },
    initListeners() {
        return session.data.self_ordering_mode === "mobile"
            ? super.initListeners(...arguments)
            : true;
    },
    synchronizeLocalDataInIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? super.synchronizeLocalDataInIndexedDB(...arguments)
            : true;
    },
    async getCachedServerDataFromIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? await super.getCachedServerDataFromIndexedDB(...arguments)
            : {};
    },
    async getLocalDataFromIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? await super.getLocalDataFromIndexedDB(...arguments)
            : {};
    },
    async missingRecursive(recordMap) {
        return recordMap;
    },
    async checkAndDeleteMissingOrders(results) {},
});
