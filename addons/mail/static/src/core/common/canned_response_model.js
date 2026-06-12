import { fields, Record } from "@mail/model/export";

export class CannedResponse extends Record {
    static _name = "mail.canned.response";

    /** @type {number} */
    id;
    last_used = fields.Datetime();
    /** @type {string} */
    source;
    /** @type {string} */
    substitution;
}

CannedResponse.register();
