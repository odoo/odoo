/* @odoo-module */

import { Record, modelRegistry } from "@mail/core/common/record";

export class CannedResponse extends Record {
    /** @type {Object.<number, CannedResponse>} */
    static records = {};
    /**
     * @param {Object} data
     * @returns {CannedResponse}
     */
    static insert(data) {
        let cannedResponse = this.records[data.id];
        if (!cannedResponse) {
            this.records[data.id] = new CannedResponse();
            cannedResponse = this.records[data.id];
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

modelRegistry.add(CannedResponse.name, CannedResponse);
