/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */
/* global idbKeyval */
import { loadBundle } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";
import { registry } from "@web/core/registry";

const PREFIX = "odoo-mail";
export const loadIdbAssets = memoize(async () => await loadBundle("mail.assets_idb_keyval"));

export class LocalStorage {
    constructor(env) {
        this.env = env;
        const { Store } = idbKeyval;
        this.syncStore = new Store(`${PREFIX}-sync-db`, `${PREFIX}-sync-store`);
    }

    async update(record, vals) {
        const { set } = idbKeyval;
        for (const [fieldName, value] of Object.entries(vals)) {
            if (!record.Model._.fields.get(fieldName) || record.Model._.fieldsAttr.get(fieldName)) {
                this.updateAttr(record, fieldName, value);
            } else {
                this.updateRelation(record, fieldName, value);
            }
        }
        return await set(key, value, this.syncStore);
    }

    async get(key) {
        const { get } = idbKeyval;
        return await get(key, this.syncStore);
    }

    /**
     * @param {Record} record
     * @param {Object} vals
     */
    updateFields(record, vals) {
        for (const [fieldName, value] of Object.entries(vals)) {
            if (!record.Model._.fields.get(fieldName) || record.Model._.fieldsAttr.get(fieldName)) {
                this.updateAttr(record, fieldName, value);
            } else {
                this.updateRelation(record, fieldName, value);
            }
        }
    }
}

export const localStorageService = {
    async start(env) {
        await loadIdbAssets();
        return new LocalStorage(env);
    },
};

registry.category("services").add("discuss.local_storage", localStorageService);
