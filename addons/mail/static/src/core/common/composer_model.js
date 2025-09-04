import { fields, OR, Record } from "@mail/core/common/record";
import { convertBrToLineBreak, prettifyMessageText } from "@mail/utils/common/format";
import { markup } from "@odoo/owl";
import { isHtmlEmpty } from "@web/core/utils/html";

export class Composer extends Record {
    static id = OR("thread", "message");

    clear() {
        this.attachments.length = 0;
        this.replyToMessage = undefined;
        this.composerHtml = markup("<p><br></p>");
        Object.assign(this.selection, {
            start: 0,
            end: 0,
            direction: "none",
        });
    }

    /**
     * @param {string} text - text to insert
     * @param {number} position - insertion position
     * @param {Object} [options]
     * @param {boolean} [options.moveCursorToEnd=false] - If true, place cursor at end of composerText
     */
    insertText(text, position, { moveCursorToEnd = false } = {}) {
        const before = this.composerText.substring(0, position);
        const after = this.composerText.substring(position);
        this.composerText = before + text + after;
        this.selection.start = before.length + text.length;
        if (moveCursorToEnd) {
            this.selection.start = this.composerText.length;
        }
        this.selection.end = this.selection.start;
        this.forceCursorMove = true;
    }

    attachments = fields.Many("ir.attachment");
    /** @type {boolean} */
    emailAddSignature = true;
    message = fields.One("mail.message");
    mentionedPartners = fields.Many("res.partner");
    mentionedRoles = fields.Many("res.role");
    mentionedChannels = fields.Many("Thread");
    cannedResponses = fields.Many("mail.canned.response");
    isDirty = false;
    composerText = fields.Attr("", {
        onUpdate() {
            if (this.updateFrom === "html") {
                this.updateFrom = undefined;
                return;
            }
            this.updateFrom = "text";
            const validMentions = this.store.getMentionsFromText(this.composerText, {
                mentionedChannels: this.mentionedChannels,
                mentionedPartners: this.mentionedPartners,
                mentionedRoles: this.mentionedRoles,
            });
            this.composerHtml = prettifyMessageText(this.composerText, { validMentions });
        },
    });
    composerHtml = fields.Html(markup("<p><br></p>"), {
        compute() {
            if (this.syncHtmlWithMessage) {
                return this.message.body || markup("<p><br></p>");
            }
            return this.composerHtml;
        },
        onUpdate() {
            if (this.updateFrom === "text") {
                this.updateFrom = undefined;
                return;
            }
            this.updateFrom = "html";
            this.composerText = isHtmlEmpty(this.composerHtml)
                ? ""
                : convertBrToLineBreak(this.composerHtml);
        },
    });
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
    /** @type {"text" | "html" | undefined} */
    updateFrom = undefined;

    get syncHtmlWithMessage() {
        return this.message && !this.isDirty;
    }
}

Composer.register();
