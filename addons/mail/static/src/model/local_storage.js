import { loadBundle } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";
import { registry } from "@web/core/registry";
import { openDB, deleteDB, wrap, unwrap } from 'idb';

const DB_NAME = "odoo";
const VERSION = "1.0";

export class LocalStorage {
    constructor(env) {
        this.env = env;
        // this.store = this.getStore();
    }
}

export const localStorageService = {
    start(env) {
        return new LocalStorage(env);
    },
};

registry.category("services").add("discuss.local_storage", localStorageService);
