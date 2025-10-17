import { Record } from "@mail/model/record";
import { fields } from "./record";

export class MailMessageSubtype extends Record {
    static id = "id";
    static _name = "mail.message.subtype";

    /** @type {string} */
    description;
    /** @type {string} */
    domain;
    /** @type {number} */
    id;
    /** @type {string} */
    name;

    is_custom = fields.Attr(false, {
        compute() {
            return this.field_tracked && this.field_tracked !== "";
        },
    });
    /** @type {string} */
    field_tracked;
    user_ids = fields.Many("res.users");
    /** @type {string} */
    value_update;
}
MailMessageSubtype.register();
