import { OR, Record } from "@mail/core/common/record";

export class Composer extends Record {
    static id = OR("thread", "message");

    clear() {
        this.attachments.length = 0;
        this.replyToMessage = undefined;
        this.text = "";
        Object.assign(this.selection, {
            start: 0,
            end: 0,
            direction: "none",
        });
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
    replyToMessage = Record.one("mail.message");
}

Composer.register();
