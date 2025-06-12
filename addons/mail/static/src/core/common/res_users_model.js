import { Record } from "@mail/core/common/record";

export class ResUsers extends Record {
    static _name = "res.users";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {boolean} */
    is_admin;
    /** @type {string} */
    name;
    /** @type {"email" | "inbox"} */
    notification_type;
    /** @type {boolean} false when the user is an internal user, true otherwise */
    share;
}

ResUsers.register();
