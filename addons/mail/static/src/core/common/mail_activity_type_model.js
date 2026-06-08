import { Record } from "@mail/model/export";

export class MailActivityType extends Record {
    static _name = "mail.activity.type";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

MailActivityType.register();
