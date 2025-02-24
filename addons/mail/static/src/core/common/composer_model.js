import { OR, Record } from "@mail/core/common/record";

export class Composer extends Record {
    static id = OR("thread", "message");

    clear() {
        this.htmlBody = "<p><br/></p>";
        this.attachments.length = 0;
    }

    attachments = Record.many("ir.attachment");
    /** @type {boolean} */
    emailAddSignature = true;
    message = Record.one("mail.message");
    mentionedPartners = Record.many("Persona");
    mentionedChannels = Record.many("Thread");
    cannedResponses = Record.many("mail.canned.response");
    htmlBody = "<p><br/></p>";
    thread = Record.one("Thread");
    /** @type {boolean} */
    forceCursorMove;
    isFocused = false;
    autofocus = 0;
}

Composer.register();
