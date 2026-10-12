import { Record } from "@mail/model/export";

export class ResCompany extends Record {
    static _name = "res.company";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

ResCompany.register();
