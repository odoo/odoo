import { Record } from "@mail/core/common/record";

export class ResUsers extends Record {
    static _name = "res.users";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

ResUsers.register();
