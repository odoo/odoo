/* @odoo-module */

import { toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

export class Record {
    static records = {};
    static register() {
        modelRegistry.add(this.name, this);
    }

    /**
     * @param {Object} data
     * @returns {Record}
     */
    static insert(data) {}

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

Record.register();
