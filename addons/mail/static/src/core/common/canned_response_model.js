import { Record } from "@mail/core/common/record";

export class CannedResponse extends Record {
    static _name = "mail.canned.response";
    static id = "id";
    /** @type {Object.<number, import("models").CannedResponse>} */
    static records = {};
    /** @returns {import("models").CannedResponse} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").CannedResponse|import("models").CannedResponse[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {number} */
    id;
    /** @type {string} */
    source;
    /** @type {string} */
    substitution;
}

CannedResponse.register();
