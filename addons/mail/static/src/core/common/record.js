/* @odoo-module */

import { toRaw } from "@odoo/owl";

export class Record {
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
