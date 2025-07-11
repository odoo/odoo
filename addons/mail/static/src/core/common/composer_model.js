import { fields, OR, Record } from "@mail/core/common/record";
import { markup } from "@odoo/owl";

export class Composer extends Record {
    static id = OR("thread", "message");

    clear() {
        this.attachments.length = 0;
        this.replyToMessage = undefined;
        this.text = "";
        this.body = markup("<p><br></p>");
        Object.assign(this.selection, {
            start: 0,
            end: 0,
            direction: "none",
        });
    }

    attachments = fields.Many("ir.attachment");
    body = markup("<p><br></p>");
    /** @type {boolean} */
    emailAddSignature = true;
    message = fields.One("mail.message");
    mentionedPartners = fields.Many("Persona");
    mentionedRoles = fields.Many("res.role");
    mentionedChannels = fields.Many("Thread");
    cannedResponses = fields.Many("mail.canned.response");
    text = "";
    thread = fields.One("Thread");
    /** @type {{ start: number, end: number, direction: "forward" | "backward" | "none"}}*/
    selection = {
        start: 0,
        end: 0,
        direction: "none",
    };
    /** @type {boolean} */
    forceCursorMove;
    isFocused = fields.Attr(false, {
        /** @this {import("models").Composer} */
        onUpdate() {
            if (this.thread) {
                if (this.isFocused) {
                    this.thread.isFocusedCounter++;
                } else {
                    this.thread.isFocusedCounter--;
                }
            }
        },
    });
    autofocus = 0;
    replyToMessage = fields.One("mail.message");
}

Composer.register();
