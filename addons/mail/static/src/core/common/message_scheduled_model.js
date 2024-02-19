import { Record } from "@mail/core/common/record";
import { deserializeDateTime } from "@web/core/l10n/dates";

export class ScheduledMessage extends Record {
    casts = { date: deserializeDateTime };
    static id = "id";
    /** @type {Object.<number, import("models").Country>} */
    static records = {};
    /** @returns {import("models").Country} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Country|import("models").Country[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    thread = Record.one("Thread", { inverse: "scheduledMessages" });
    author = Record.one("Persona");
    /** @type {number} */
    id;
    /** @type {luxon.DateTime} */
    date = Record.attr(undefined, { type: "datetime" });
    /** @type {string} */
    thread_model;
    /** @type {Number} */
    thread_id;
}

ScheduledMessage.register();
