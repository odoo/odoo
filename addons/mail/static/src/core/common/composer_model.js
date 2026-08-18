import { fields, OR, Record } from "@mail/model/export";
import {
    convertBrToLineBreak,
    prepareBodyForEditing,
    generatePartnerMentionElement,
    prettifyMessageText,
} from "@mail/utils/common/format";
import { createElementFromContent, getInnerHtml } from "@mail/utils/common/html";
import { markup } from "@odoo/owl";
import { isHtmlEmpty } from "@web/core/utils/html";
import { nbsp } from "@web/core/utils/strings";

export class Composer extends Record {
    static id = OR("thread", "message");

    setup() {
        super.setup();
        this.onRelationChange(
            () => [this.thread, this.message],
            ({ removed }) => {
                if (removed.length && !this.thread && !this.message) {
                    this.delete();
                }
            }
        );
        this.onChange(
            () => [this.syncHtmlWithMessage, this.message?.body],
            function onChangeSyncHtmlWithMessage(syncHtmlWithMessage, messageBody) {
                if (syncHtmlWithMessage) {
                    this.updateFrom = "html";
                    this.composerHtml =
                        prepareBodyForEditing(messageBody) ||
                        markup("<div class='o-paragraph'><br></div>");
                }
            }
        );
        this.onChange(
            () => [this.composerText],
            function onChangeComposerText(composerText) {
                if (this.updateFrom === "html") {
                    this.updateFrom = undefined;
                    return;
                }
                const validMentions = this.store.getMentionsFromText(composerText, {
                    mentionedPartners: this.mentionedPartners,
                    mentionedRoles: this.mentionedRoles,
                    thread: this.targetThread,
                });
                const prettifiedHtml = composerText
                    ? prettifyMessageText(composerText, {
                          validMentions,
                          thread: this.targetThread,
                          trim: false,
                      })
                    : markup("<div class='o-paragraph'><br></div>");
                if (this.composerHtml.toString() !== prettifiedHtml.toString()) {
                    this.updateFrom = "text";
                    this.composerHtml = prettifiedHtml;
                }
            },
            { immediate: true }
        );
        this.onChange(
            () => [this.composerHtml],
            function onChangeComposerHtml(composerHtml) {
                if (this.updateFrom === "text") {
                    this.updateFrom = undefined;
                    return;
                }
                const prettifiedText = isHtmlEmpty(composerHtml)
                    ? ""
                    : convertBrToLineBreak(composerHtml, { trim: false });
                if (this.composerText !== prettifiedText) {
                    this.updateFrom = "html";
                    this.composerText = prettifiedText;
                }
            },
            { immediate: true }
        );
        this.onChange(
            () => [this.thread, this.isFocused],
            function onChangeIsFocused(thread, isFocused) {
                if (thread && isFocused) {
                    thread.isFocusedCounter++;
                    return () => thread.isFocusedCounter--;
                }
            },
            { immediate: true, initialRun: false }
        );
    }

    clear() {
        this.attachments.length = 0;
        this.replyToMessage = undefined;
        this.restoredFromFullComposer = false;
        if (this.updateFrom === "html") {
            this.composerHtml = markup("<div class='o-paragraph'><br></div>");
        } else {
            this.composerText = "";
        }
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
    isEditComposerVisible = false;
    message = fields.One("mail.message");
    mentionedPartners = fields.Many("res.partner");
    mentionedRoles = fields.Many("res.role");
    cannedResponses = fields.Many("mail.canned.response");
    isDirty = false;
    composerText = "";
    composerHtml = fields.Html(markup("<div class='o-paragraph'><br></div>"));
    thread = fields.One("mail.thread");
    /** @type {{ start: number, end: number, direction: "forward" | "backward" | "none"}}*/
    selection = fields.Attr(
        {
            start: 0,
            end: 0,
            direction: "none",
        },
        { asProxy: true }
    );
    /** @type {boolean} */
    forceCursorMove;
    isFocused = false;
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
        const composerBody = createElementFromContent(this.composerHtml);
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
