import { Record } from "@mail/core/common/record";

export class CannedResponse extends Record {
    static _name = "mail.canned.response";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    source;
    /** @type {string} */
    substitution;
}

CannedResponse.register();
