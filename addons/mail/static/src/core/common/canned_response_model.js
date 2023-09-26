/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class CannedResponse extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").CannedResponse>} */
    static records = {};
    /** @returns {import("models").CannedResponse} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {import("models").CannedResponse}
     */
    static insert(data) {
        /** @type {import("models").CannedResponse} */
        const cannedResponse = this.preinsert(data);
        Object.assign(cannedResponse, {
            id: data.id,
            name: data.source,
            substitution: data.substitution,
        });
        return cannedResponse;
    }

    /** @type {number} */
    id;
    /** @type {string} */
    name;
    /** @type {string} */
    substitution;
}

CannedResponse.register();
