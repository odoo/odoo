import { Record } from "@mail/model/record";

export class MailMessageSubtype extends Record {
    static id = "id";
    static _name = "mail.message.subtype";

    /** @type {string} */
    description;
    /** @type {number} */
    id;
    /** @type {string} */
    name;
}
MailMessageSubtype.register();
