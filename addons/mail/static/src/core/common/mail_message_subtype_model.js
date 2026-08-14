import { Record } from "@mail/model/record";

export class MailMessageSubtype extends Record {
    static _name = "mail.message.subtype";

    /** @type {number} */
    id;
}
MailMessageSubtype.register();
