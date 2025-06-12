import { Record } from "@mail/core/common/record";

export class ResUsers extends Record {
    static _name = "res.users";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
    /** @type {boolean} false when the user is an internal user, true otherwise */
    share;
}

ResUsers.register();
