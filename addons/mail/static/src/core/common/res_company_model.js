import { Record } from "@mail/core/common/record";

export class ResCompany extends Record {
    static _name = "res.company";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

ResCompany.register();
