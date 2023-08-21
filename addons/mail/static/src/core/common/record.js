/* @odoo-module */

import { createLocalId } from "@mail/utils/common/misc";
import { toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

export class Record {
    /** @type {import("@web/env").OdooEnv} env */
    static env;
    /** @type {Object.<number, Record>} */
    static records = {};
    /** @type {import("@mail/core/common/store_service").Store */
    static store;
    static ids = [];

    /**
     * @param {Object} data
     * @returns {Record}
     */
    static findById(data) {}

    /**
     * @param {Object} data
     * @returns {Record}
     */
    static insert(data) {}

    get objId() {
        return createLocalId(
            this.constructor.name,
            ...this.constructor.ids.map((name) => this[name])
        );
    }

    /** @param {Record} record */
    eq(record) {
        return toRaw(this) === toRaw(record);
    }

    /** @param {Record} record */
    notEq(record) {
        return !this.eq(record);
    }

    /** @param {Record[]} list */
    in(list) {
        return list.some((record) => record.eq(this));
    }

    /** @param {Record[]} list */
    notIn(list) {
        return !this.in(list);
    }
}
