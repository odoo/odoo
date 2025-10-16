import { fields, Record } from "@mail/core/common/record";

export class ResUsers extends Record {
    static _name = "res.users";
    static _inherits = { "res.partner": "partner_id" };
    static id = "id";

    /** @type {number} */
    id;
    company_id = fields.One("res.company");
    /** @type {string} */
    im_status;
    /** @type {boolean} */
    is_admin;
    /** @type {"email" | "inbox"} */
    notification_type;
    partner_id = fields.One("res.partner", { inverse: "user_ids" });
    /** @type {boolean} false when the user is an internal user, true otherwise */
    share;
    /** @type {ReturnType<import("@odoo/owl").markup>|string|undefined} */
    signature = fields.Html(undefined);
}

ResUsers.register();
