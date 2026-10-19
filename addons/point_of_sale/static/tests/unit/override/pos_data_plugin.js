import { PosDataPlugin } from "@point_of_sale/app/plugins/pos_data_plugin";
import { patch } from "@web/core/utils/patch";

/**
 * Disable IndexedDB in Hoot tests to avoid creating to much IndexedDB databases
 * when running the full test suite.
 *
 * IndexedDB is still tested in dedicated tours.
 */
patch(PosDataPlugin.prototype, {
    setup() {
        this.indexedDB = {
            delete: async () => ({}),
            create: async () => ({}),
            reset: async () => ({}),
            readAll: async () => ({}),
            readAllExceptStores: async () => ({}),
            dbStores: [],
        };
        return super.setup(...arguments);
    },
    initIndexedDB() {
        return true;
    },
    initListeners() {
        return true;
    },
    synchronizeLocalDataInIndexedDB() {
        return true;
    },
    async getCachedServerDataFromIndexedDB() {
        return {};
    },
    async getLocalDataFromIndexedDB() {
        return {};
    },
    async deleteRecordsInIndexedDB() {
        return true;
    },
    async getCachedServerIdsFromIndexedDB() {
        return {};
    },
});
