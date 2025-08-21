import { fields, OR, Record } from "@mail/core/common/record";
import { convertBrToLineBreak, prettifyMessageContent } from "@mail/utils/common/format";

export class Composer extends Record {
    static id = OR("thread", "message");

    clear() {
        this.attachments.length = 0;
        this.replyToMessage = undefined;
        this.composerHtml = "";
        Object.assign(this.selection, {
            start: 0,
            end: 0,
            direction: "none",
        });
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
        compute() {
            if (this.syncTextWithMessage) {
                return convertBrToLineBreak(this.message.body || "");
            }
            return this.composerText;
        },
        onUpdate() {
            if (this.updateFromHtml) {
                return;
            }
            const validMentions = this.store.getMentionsFromText(this.composerText, {
                mentionedChannels: this.mentionedChannels,
                mentionedPartners: this.mentionedPartners,
                mentionedRoles: this.mentionedRoles,
            });
            prettifyMessageContent(this.composerText, { validMentions }).then((content) => {
                this.updateFromText = true;
                this.composerHtml = content;
                this.updateFromText = false;
            });
        },
    });
    composerHtml = fields.Html("", {
        onUpdate() {
            if (this.updateFromText) {
                return;
            }
            this.updateFromHtml = true;
            this.composerText = convertBrToLineBreak(this.composerHtml);
            this.updateFromHtml = false;
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
    updateFromText = false;
    updateFromHtml = false;

    get syncTextWithMessage() {
        return this.message && !this.isDirty;
    }
}

Composer.register();
