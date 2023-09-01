/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class CannedResponse extends Record {
    static id = "id";
    /** @type {Object.<number, CannedResponse>} */
    static records = {};
    /**
     * @param {Object} data
     * @returns {CannedResponse}
     */
    static insert(data) {
        const cannedResponse = this.get(data) ?? this.new(data);
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
