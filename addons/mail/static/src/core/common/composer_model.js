import { OR, Record } from "@mail/core/common/record";
import { convertBrToLineBreak } from "@mail/utils/common/format";

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

    attachments = Record.many("ir.attachment");
    /** @type {boolean} */
    emailAddSignature = true;
    message = Record.one("mail.message");
    mentionedPartners = Record.many("Persona");
    mentionedChannels = Record.many("Thread");
    cannedResponses = Record.many("mail.canned.response");
    isDirty = false;
    text = Record.attr("", {
        compute() {
            if (!this.isDirty && this.message) {
                return convertBrToLineBreak(this.message.body || "");
            }
            return this.text;
        },
    });
    thread = Record.one("Thread");
    /** @type {{ start: number, end: number, direction: "forward" | "backward" | "none"}}*/
    selection = {
        start: 0,
        end: 0,
        direction: "none",
    };
    /** @type {boolean} */
    forceCursorMove;
    isFocused = Record.attr(false, {
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
}

Composer.register();
