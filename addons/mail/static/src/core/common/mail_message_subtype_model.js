import { Record } from "@mail/model/record";

export class MailMessageSubtype extends Record {
    static _name = "mail.message.subtype";

    /** @type {string} */
    description;
    /** @type {number} */
    id;
    /** @type {string} */
    name;
    /** @type {number|false} */
    parent_id;
}
MailMessageSubtype.register();
