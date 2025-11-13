import { PosData } from "@point_of_sale/app/services/data_service";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

export const unpatchSelf = patch(PosData.prototype, {
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
    get databaseName() {
        return `pos-self-order-${odoo.access_token}`;
    },
    async initializeDeviceIdentifier() {
        return false;
    },
    initIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? super.initIndexedDB(...arguments)
            : true;
    },
    async resetIndexedDB() {
        return session.data.self_ordering_mode === "mobile"
            ? await super.resetIndexedDB(...arguments)
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
    async synchronizeServerDataInIndexedDB(serverData = {}) {
        return session.data.self_ordering_mode === "mobile"
            ? super.synchronizeServerDataInIndexedDB(...arguments)
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
    async getCachedServerIdsFromIndexedDB(models = []) {
        return session.data.self_ordering_mode === "mobile"
            ? await super.getCachedServerIdsFromIndexedDB(...arguments)
            : {};
    },
    async cleanOldModels(localData, data) {
        return session.data.self_ordering_mode === "mobile"
            ? await super.cleanOldModels(...arguments)
            : true;
    },
    async cleanLocalData(data, localData) {
        return session.data.self_ordering_mode === "mobile"
            ? await super.cleanLocalData(...arguments)
            : true;
    },
    async missingRecursive(recordMap) {
        return recordMap;
    },
    async checkAndDeleteMissingOrders(results) {},
});
