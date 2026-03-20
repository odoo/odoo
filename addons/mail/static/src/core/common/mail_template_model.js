import { Record } from "@mail/model/record";

export class MailTemplate extends Record {
    static _name = "mail.template";
    /** @type {number} */
    id;
    /** @type {String} */
    name;
}
MailTemplate.register();
