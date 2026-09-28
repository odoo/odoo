import { fields, OR, Record } from "@mail/model/export";
import {
    convertBrToLineBreak,
    prepareBodyForEditing,
    generatePartnerMentionElement,
} from "@mail/utils/common/format";
import { createElementFromContent, getInnerHtml } from "@mail/utils/common/html";
import { markup } from "@odoo/owl";
import { isHtmlEmpty } from "@web/core/utils/html";
import { nbsp } from "@web/core/utils/strings";

export class Composer extends Record {
    static id = OR("thread", "message");

    setup() {
        super.setup(...arguments);
        this.onChange(
            () => [this.composerHtml],
            function onChangeComposerHtml(composerHtml) {
                this.composerText = isHtmlEmpty(composerHtml)
                    ? ""
                    : convertBrToLineBreak(composerHtml, { trim: false });
            },
            { immediate: true, initialRun: false }
        );
        this.onChange(
            () => [this.message?.body],
            function onChangeMessageBody(body) {
                if (this.syncHtmlWithMessage) {
                    this.composerHtml = prepareBodyForEditing(body);
                }
            },
            { immediate: true, initialRun: false }
        );
        this.onChange(
            () => [this.isFocused, this.thread],
            function onChangeIsFocused(isFocused, thread) {
                if (thread && isFocused) {
                    thread.isFocusedCounter++;
                    return () => thread.isFocusedCounter--;
                }
            },
            { immediate: true }
        );
    }

    clear() {
        this.attachments.length = 0;
        this.replyToMessage = undefined;
        this.restoredFromFullComposer = false;
        this.composerHtml = markup("<div class='o-paragraph'><br></div>");
    }

    /**
     * Appends plain text on a new line at the end of the content.
     *
     * @param {string} text
     */
    appendText(text) {
        const composerBody = createElementFromContent(this.composerHtml);
        const doc = composerBody.ownerDocument;
        let block = composerBody.lastElementChild;
        if (!block) {
            block = doc.createElement("div");
            block.classList.add("o-paragraph");
            composerBody.append(block);
        }
        if (isHtmlEmpty(this.composerHtml)) {
            block.replaceChildren();
        } else {
            block.append(doc.createElement("br"));
        }
        text.split("\n").forEach((line, index) => {
            if (index) {
                block.append(doc.createElement("br"));
            }
            block.append(line);
        });
        this.composerHtml = getInnerHtml(composerBody);
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
    /** Plain text version of `composerHtml`, kept in sync with it. */
    composerText = "";
    composerHtml = fields.Html(markup("<div class='o-paragraph'><br></div>"));
    isComposerHtmlEmpty = this.computed(() => isHtmlEmpty(this.composerHtml));
    thread = fields.One("mail.thread");
    /**
     * Last selection in the editor, as paths from the editable, to restore it
     * when the editor is re-created with the same content.
     *
     * @type {{
     *  anchorPath: number[],
     *  anchorOffset: number,
     *  focusPath: number[],
     *  focusOffset: number,
     *  composerHtml: string,
     * }|undefined}
     */
    editorSelection;
    isFocused = false;
    autofocus = 0;
    /** When set, this means the composer content was restored from local storage, and content was saved from full composer */
    restoredFromFullComposer = false;
    replyToMessage = fields.One("mail.message", { inverse: "composerAsReplyToMessage" });

    get syncHtmlWithMessage() {
        return this.message && !this.isDirty;
    }

    get targetThread() {
        return this.replyToMessage?.thread ?? this.thread ?? this.message?.thread ?? null;
    }

    /** @param {import("models").Message} message */
    insertReplyFromNote(message) {
        this.mentionedPartners.add(message.author);
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
