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
        this.text = "<p><br/></p>";
        this.attachments.length = 0;
    }

    attachments = Record.many("ir.attachment");
    /** @type {boolean} */
    emailAddSignature = true;
    message = Record.one("mail.message");
    mentionedPartners = Record.many("Persona");
    mentionedChannels = Record.many("Thread");
    cannedResponses = Record.many("mail.canned.response");
    text = "";
    thread = Record.one("Thread");
    /** @type {boolean} */
    forceCursorMove;
    isFocused = false;
    autofocus = 0;
}

Composer.register();
