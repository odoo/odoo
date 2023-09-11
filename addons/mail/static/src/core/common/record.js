/* @odoo-module */

import { toRaw } from "@odoo/owl";

export class Record {
    /** @param {Record} record */
    eq(record) {
        return toRaw(this) === toRaw(record);
    }
}
