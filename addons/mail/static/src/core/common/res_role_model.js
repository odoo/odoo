import { Record } from "@mail/core/common/record";

export class ResRole extends Record {
    static id = "id";
    static _name = "res.role";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

ResRole.register();
