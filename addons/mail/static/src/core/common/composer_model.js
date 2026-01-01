import { fields, OR, Record } from "@mail/model/export";
import {
    convertBrToLineBreak,
    prepareBodyForEditing,
    generatePartnerMentionElement,
    prettifyMessageText,
} from "@mail/utils/common/format";
import { getInnerHtml } from "@mail/utils/common/html";
import { markup } from "@odoo/owl";
import { createDocumentFragmentFromContent, isHtmlEmpty } from "@web/core/utils/html";
import { nbsp } from "@web/core/utils/strings";

export class Composer extends Record {
    static id = OR("thread", "message");

    clear() {
        this.attachments.length = 0;
        this.replyToMessage = undefined;
        this.restoredFromFullComposer = false;
        this.composerHtml = markup("<div class='o-paragraph'><br></div>");
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
    mentionedChannels = fields.Many("discuss.channel");
    cannedResponses = fields.Many("mail.canned.response");
    isDirty = false;
    composerText = fields.Attr("", {
        onUpdate() {
            if (this.updateFrom === "html") {
                this.updateFrom = undefined;
                return;
            }
            const validMentions = this.store.getMentionsFromText(this.composerText, {
                mentionedChannels: this.mentionedChannels,
                mentionedPartners: this.mentionedPartners,
                mentionedRoles: this.mentionedRoles,
                thread: this.targetThread,
            });
            const prettifiedHtml = prettifyMessageText(this.composerText, {
                validMentions,
                thread: this.targetThread,
            });
            if (this.composerHtml.toString() !== prettifiedHtml.toString()) {
                this.updateFrom = "text";
                this.composerHtml = prettifiedHtml;
            }
        },
    });
    composerHtml = fields.Html(markup("<div class='o-paragraph'><br></div>"), {
        compute() {
            if (this.syncHtmlWithMessage) {
                return (
                    prepareBodyForEditing(this.message.body) ||
                    markup("<div class='o-paragraph'><br></div>")
                );
            }
            return this.composerHtml;
        },
        onUpdate() {
            if (this.updateFrom === "text") {
                this.updateFrom = undefined;
                return;
            }
            const prettifiedText = isHtmlEmpty(this.composerHtml)
                ? ""
                : convertBrToLineBreak(this.composerHtml);
            if (this.composerText !== prettifiedText) {
                this.updateFrom = "html";
                this.composerText = prettifiedText;
            }
        },
    });
    thread = fields.One("mail.thread");
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
    /** When set, this means the composer content was restored from local storage, and content was saved from full composer */
    restoredFromFullComposer = false;
    replyToMessage = fields.One("mail.message", { inverse: "composerAsReplyToMessage" });
    /** @type {"text" | "html" | undefined} */
    updateFrom = undefined;

    get syncHtmlWithMessage() {
        return this.message && !this.isDirty;
    }

    get targetThread() {
        return this.replyToMessage?.thread ?? this.thread ?? this.message?.thread ?? null;
    }

    /** @param {import("models").Message} message */
    insertReplyFromNote(message) {
        this.mentionedPartners.add(message.author);
        if (!this.store.env.services["mail.composer"].htmlEnabled) {
            const mentionText = `@${message.authorName} `;
            if (!this.composerText.includes(mentionText)) {
                this.insertText(mentionText, 0, { moveCursorToEnd: true });
            }
            return;
        }
        const composerBody = createDocumentFragmentFromContent(this.composerHtml).body;
        if (
            composerBody.querySelector(
                `a.o_mail_redirect[data-oe-model="res.partner"][data-oe-id="${message.author.id}"]`
            )
        ) {
            return;
        }
        composerBody.firstElementChild.prepend(
            generatePartnerMentionElement(message.author, this.thread),
            nbsp
        );
        this.composerHtml = getInnerHtml(composerBody);
    }
}

Composer.register();
