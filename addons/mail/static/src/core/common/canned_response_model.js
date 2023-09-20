/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class CannedResponse extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Models["CannedResponse"]>} */
    static records = {};
    /** @returns {import("models").Models["CannedResponse"]} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {import("models").Models["CannedResponse"]} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {import("models").Models["CannedResponse"]}
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
