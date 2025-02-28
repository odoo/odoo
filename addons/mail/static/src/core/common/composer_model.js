import { OR, Record } from "@mail/core/common/record";
import { isEmpty } from "@mail/utils/common/format";

export class Composer extends Record {
    static id = OR("thread", "message");

    clear() {
        this.attachments.length = 0;
        this.text = "";
        this.htmlBody = "<p><br></p>";
        Object.assign(this.selection, {
            start: 0,
            end: 0,
            direction: "none",
        });
    }
    isBodyEmpty() {
        return !this.text && isEmpty(this.htmlBody);
    }
    attachments = Record.many("ir.attachment");
    /** @type {boolean} */
    emailAddSignature = true;
    message = Record.one("mail.message");
    mentionedPartners = Record.many("Persona");
    mentionedChannels = Record.many("Thread");
    cannedResponses = Record.many("mail.canned.response");
    text = "";
    htmlBody = "<p><br></p>";
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
