import { PosData } from "@point_of_sale/app/services/data_service";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";

export const unpatchSelf = patch(PosData.prototype, {
    async loadInitialData() {
        const configId = session.data.config_id;
        return await rpc(`/pos-self/data/${parseInt(configId)}`, {
            access_token: odoo.access_token,
        });
    },
    async loadFieldsAndRelations() {
        const configId = session.data.config_id;
        return await rpc(`/pos-self/relations/${parseInt(configId)}`);
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
    async deleteRecordsInIndexedDB(model, ids) {
        return session.data.self_ordering_mode === "mobile"
            ? await super.deleteRecordsInIndexedDB(...arguments)
            : true;
    },
});
