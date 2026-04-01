import { Record } from "@mail/core/common/record";

export class MailActivityType extends Record {
    static _name = "mail.activity.type";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

MailActivityType.register();
