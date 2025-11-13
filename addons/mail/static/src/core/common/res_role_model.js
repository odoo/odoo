import { Record } from "@mail/model/export";

export class ResRole extends Record {
    static id = "id";
    static _name = "res.role";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

ResRole.register();
