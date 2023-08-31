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
        let cannedResponse = this.get(data);
        if (!cannedResponse) {
            cannedResponse = this.new(data);
            this.records[cannedResponse.localId] = cannedResponse;
            cannedResponse = this.records[cannedResponse.localId];
        }
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
