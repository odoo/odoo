import { Record } from "@mail/core/common/record";

export class MailGuest extends Record {
    static id = "id";
    static _name = "mail.guest";
    /** @type {Object.<number, import("models").MailGuest>} */
    static records = {};
    /** @returns {import("models").MailGuest} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").MailGuest|import("models").MailGuest[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    /** @type {number} */
    id;
    persona = Record.one("Persona", {
        /** @this {import("models").MailGuest} */
        compute() {
            return { id: this.id, type: "guest" };
        },
        inverse: "guest",
    });
}

MailGuest.register();
