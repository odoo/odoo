import { Record } from "@mail/model/export";

export class MailActivityType extends Record {
    static _name = "mail.activity.type";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

MailActivityType.register();
