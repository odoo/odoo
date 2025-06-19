import { Record } from "@mail/core/common/record";

export class CrmLead extends Record {
    static id = "id";
    static _name = "crm.lead";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

CrmLead.register();
