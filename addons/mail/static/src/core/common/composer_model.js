import { OR, Record } from "@mail/core/common/record";

export class Composer extends Record {
    static id = OR("thread", "message");
    /** @returns {import("models").Composer} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Composer|import("models").Composer[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    clear() {
        this.attachments.length = 0;
        this.text = "";
        Object.assign(this.selection, {
            start: 0,
            end: 0,
            direction: "none",
        });
    }

    attachments = Record.many("Attachment");
    message = Record.one("Message");
    mentionedPartners = Record.many("Persona");
    mentionedChannels = Record.many("Thread");
    cannedResponses = Record.many("mail.canned.response");
    text = "";
    thread = Record.one("Thread");
    /** @type {{ start: number, end: number, direction: "forward" | "backward" | "none"}}*/
    selection = {
        start: 0,
        end: 0,
        direction: "none",
    };
    /** @type {boolean} */
    forceCursorMove;
    isFocused = false;
    autofocus = 0;
}

Composer.register();
