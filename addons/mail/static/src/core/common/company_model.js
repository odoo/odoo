import { Record } from "@mail/core/common/record";

export class Company extends Record {
    static _name = "res.company";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

Company.register();
