import { Record } from "@mail/model/export";

export class ResRole extends Record {
    static _name = "res.role";

    /** @type {number} */
    id;
    /** @type {string} */
    color;
    /** @type {string} */
    name;
    /** @type {number} */
    sequence;
    /** @type {number} */
    user_ids_count;
}

ResRole.register();
