import { fields, Record } from "@mail/core/common/record";
import { stateToUrl } from "@web/core/browser/router";

export class CrmLead extends Record {
    static id = "id";
    static _name = "crm.lead";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
    href = fields.Attr("", {
        compute() {
            return stateToUrl({ model: 'crm.lead', resId: this.id });
        }
    });
}

CrmLead.register();
