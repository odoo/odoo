import { Record } from "@mail/model/export";

export class ResCompany extends Record {
    static _name = "res.company";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

ResCompany.register();
