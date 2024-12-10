import { Record } from "@mail/core/common/record";

export class ResUsers extends Record {
    static id = "id";
    static _name = "res.users";
    /** @type {Object.<number, import("models").ResUsers>} */
    static records = {};
    /** @returns {import("models").ResUsers} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").ResUsers|import("models").ResUsers[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    /** @type {number} */
    id;
    /** @type {"email" | "inbox"} */
    notification_type;
    partner_id = Record.one("res.partner", { inverse: "user_ids" });
    /** @type {boolean} */
    share;
}

ResUsers.register();
