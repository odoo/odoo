import { Record } from "@mail/model/export";

export class CannedResponse extends Record {
    static _name = "mail.canned.response";

    /** @type {number} */
    id;
    /** @type {string} */
    source;
    /** @type {string} */
    substitution;
}

CannedResponse.register();
