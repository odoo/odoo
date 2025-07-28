import { fields, Record } from "@mail/core/common/record";
import {
    EMOJI_REGEX,
    convertBrToLineBreak,
    decorateEmojis,
    htmlToTextContentInline,
    prettifyMessageContent,
} from "@mail/utils/common/format";

import { browser } from "@web/core/browser/browser";
import { stateToUrl } from "@web/core/browser/router";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { createDocumentFragmentFromContent, createElementWithContent } from "@web/core/utils/html";
import { url } from "@web/core/utils/urls";

import { markup } from "@odoo/owl";

const { DateTime } = luxon;
export class Message extends Record {
    static _name = "mail.message";
    static id = "id";

    /** @param {Object} data */
    update(data) {
        super.update(data);
        if (this.isNotification && !this.notificationType) {
            const htmlBody = createDocumentFragmentFromContent(this.body);
            this.notificationType = htmlBody.querySelector(".o_mail_notification")?.dataset.oeType;
        }
    }

    attachment_ids = fields.Many("ir.attachment", { inverse: "message" });
    author_id = fields.One("res.partner");
    author_guest_id = fields.One("mail.guest");
    get author() {
        return this.author_id || this.author_guest_id;
    }
    body = fields.Html("");
    call_history_ids = fields.Many("discuss.call.history");
    richBody = fields.Html("", {
        compute() {
            if (!this.store.emojiLoader.loaded) {
                loadEmoji();
            }
            return decorateEmojis(this.body) ?? "";
        },
    });
    richTranslationValue = fields.Html("", {
        compute() {
            if (!this.store.emojiLoader.loaded) {
                loadEmoji();
            }
            return decorateEmojis(this.translationValue) ?? "";
        },
    });
    composer = fields.One("Composer", { inverse: "message", onDelete: (r) => r.delete() });
    date = fields.Datetime();
    /** @type {string} */
    default_subject;
    /** @type {boolean} */
    edited = fields.Attr(false, {
        compute() {
            return Boolean(
                // ".o-mail-Message-edited" is the class added by the mail.thread in _message_update_content
                // when the message is edited
                createDocumentFragmentFromContent(this.body).querySelector(".o-mail-Message-edited")
            );
        },
    });
    hasLink = fields.Attr(false, {
        compute() {
            if (this.isBodyEmpty) {
                return false;
            }
            const div = createElementWithContent("div", this.body);
            return Boolean(div.querySelector("a:not([data-oe-model])"));
        },
    });
    /** @type {number|string} */
    id;
    /** @type {Array[Array[string]]} */
    incoming_email_cc;
    /** @type {Array[Array[string]]} */
    incoming_email_to;
    get isDiscussion() {
        return this.store.mt_comment?.eq(this.subtype_id);
    }
    get isNote() {
        return this.store.mt_note?.eq(this.subtype_id);
    }
    /** @type {boolean} */
    is_transient;
    message_link_preview_ids = fields.Many("mail.message.link.preview", { inverse: "message_id" });
    /** @type {number[]} */
    parent_id = fields.One("mail.message");
    /**
     * When set, this temporary/pending message failed message post, and the
     * value is a callback to re-attempt to post the message.
     *
     * @type {() => {} | undefined}
     */
    postFailRedo = undefined;
    reactions = fields.Many("MessageReactions", {
        inverse: "message",
        /**
         * @param {import("models").MessageReactions} r1
         * @param {import("models").MessageReactions} r2
         */
        sort: (r1, r2) => r1.sequence - r2.sequence,
    });
    notification_ids = fields.Many("mail.notification", { inverse: "mail_message_id" });
    partner_ids = fields.Many("res.partner");
    subtype_id = fields.One("mail.message.subtype");
    thread = fields.One("Thread");
    threadAsNeedaction = fields.One("Thread", {
        compute() {
            if (this.needaction) {
                return this.thread;
            }
        },
    });
    threadAsNewest = fields.One("Thread");
    threadAsInEdition = fields.One("Thread", {
        compute() {
            if (this.composer) {
                return this.thread;
            }
        },
    });
    scheduledDatetime = fields.Datetime();
    onlyEmojis = fields.Attr(false, {
        compute() {
            const bodyWithoutTags = createElementWithContent("div", this.body).textContent;
            const withoutEmojis = bodyWithoutTags.replace(EMOJI_REGEX, "");
            return (
                bodyWithoutTags.length > 0 &&
                bodyWithoutTags.match(EMOJI_REGEX) &&
                withoutEmojis.trim().length === 0
            );
        },
    });
    /** @type {string} */
    subject;
    /** @type {Object[]} */
    trackingValues = [];
    /** @type {string|undefined} */
    translationValue;
    /** @type {string|undefined} */
    translationSource;
    /** @type {string|undefined} */
    translationErrors;
    /** @type {string} */
    message_type;
    /** @type {string|undefined} */
    notificationType;
    create_date = fields.Datetime();
    write_date = fields.Datetime();
    /** @type {undefined|Boolean} */
    needaction;
    starred = false;

    /**
     * True if the backend would technically allow edition
     * @returns {boolean}
     */
    get allowsEdition() {
        return this.store.self.main_user_id?.is_admin || this.isSelfAuthored;
    }

    get bubbleColor() {
        if (this.message_type === "notification") {
            return undefined;
        }
        if (!this.isSelfAuthored && !this.isNote && !this.isHighlightedFromMention) {
            return "blue";
        }
        if (this.isSelfAuthored && !this.isNote && !this.isHighlightedFromMention) {
            return "green";
        }
        if (this.isHighlightedFromMention) {
            return "orange";
        }
        return undefined;
    }

    get editable() {
        if (this.isEmpty || !this.allowsEdition) {
            return false;
        }
        return this.message_type === "comment";
    }

    get dateDay() {
        let dateDay = this.datetime.toLocaleString(DateTime.DATE_MED);
        if (dateDay === DateTime.now().toLocaleString(DateTime.DATE_MED)) {
            dateDay = _t("Today");
        }
        return dateDay;
    }

    get dateSimple() {
        return this.datetime
            .toLocaleString(DateTime.TIME_SIMPLE, {
                locale: user.lang,
            })
            .replace(" ", " "); // so that AM/PM are properly wrapped
    }

    get dateSimpleWithDay() {
        const userLocale = { locale: user.lang };
        if (this.datetime.hasSame(DateTime.now(), "day")) {
            return this.datetime.toLocaleString(DateTime.TIME_SIMPLE, userLocale);
        }
        if (this.datetime.hasSame(DateTime.now().minus({ day: 1 }), "day")) {
            return _t("Yesterday at %(time)s", {
                time: this.datetime.toLocaleString(DateTime.TIME_SIMPLE, userLocale),
            });
        }
        if (this.datetime?.year === DateTime.now().year) {
            return this.datetime.toLocaleString(
                { ...DateTime.DATETIME_MED, year: undefined },
                userLocale
            );
        }
        return this.datetime.toLocaleString({ ...DateTime.DATETIME_MED }, userLocale);
    }

    get datetime() {
        return this.date || DateTime.now();
    }

    /**
     * Get the effective persona performing actions on this message.
     * Priority order: logged-in user, portal partner (token-authenticated), guest.
     *
     * @returns {import("models").Persona}
     */
    get effectiveSelf() {
        return this.thread?.effectiveSelf ?? this.store.self;
    }

    get datetimeShort() {
        return this.datetime.toLocaleString(DateTime.DATETIME_SHORT_WITH_SECONDS);
    }

    get isSelfMentioned() {
        return this.effectiveSelf.in(this.partner_ids);
    }

    get isHighlightedFromMention() {
        return this.isSelfMentioned && this.thread?.model === "discuss.channel";
    }

    isSelfAuthored = fields.Attr(false, {
        compute() {
            return Boolean(this.author?.eq(this.effectiveSelf));
        },
    });

    isPending = false;

    get hasActions() {
        return !this.is_transient;
    }

    get isNotification() {
        return this.message_type === "notification" && this.thread?.model === "discuss.channel";
    }

    get isSubjectSimilarToThreadName() {
        if (!this.subject || !this.thread || !this.thread.display_name) {
            return false;
        }
        const regexPrefix = /^((re|fw|fwd)\s*:\s*)*/i;
        const cleanedThreadName = this.thread.display_name.replace(regexPrefix, "");
        const cleanedSubject = this.subject.replace(regexPrefix, "");
        return cleanedSubject === cleanedThreadName;
    }

    get isSubjectDefault() {
        const name = this.thread?.display_name;
        const threadName = name ? name.trim().toLowerCase() : "";
        const defaultSubject = this.default_subject ? this.default_subject.toLowerCase() : "";
        const candidates = new Set([defaultSubject, threadName]);
        return candidates.has(this.subject?.toLowerCase());
    }

    get persistent() {
        return Number.isInteger(this.id);
    }

    get resUrl() {
        return url(stateToUrl({ model: this.thread.model, resId: this.thread.id }));
    }

    isTranslatable(thread) {
        return (
            !this.isEmpty &&
            this.store.hasMessageTranslationFeature &&
            !["discuss.channel", "mail.box"].includes(thread?.model)
        );
    }

    get hasTextContent() {
        return !this.isBodyEmpty;
    }

    isEmpty = fields.Attr(false, {
        /** @this {import("models").Message} */
        compute() {
            return this.computeIsEmpty();
        },
    });
    isBodyEmpty = fields.Attr(undefined, {
        compute() {
            return (
                !this.body ||
                [
                    "",
                    "<p></p>",
                    "<p><br></p>",
                    "<p><br/></p>",
                    "<div></div>",
                    "<div><br></div>",
                    "<div><br/></div>",
                ].includes(
                    this.body
                        .replace('<span class="o-mail-Message-edited"></span>', "")
                        .replace(/\s/g, "")
                )
            );
        },
    });

    computeIsEmpty() {
        return (
            this.isBodyEmpty &&
            this.attachment_ids.length === 0 &&
            this.trackingValues.length === 0 &&
            !this.subtype_id?.description
        );
    }

    /**
     * Determines if the link preview is actually the main content of the
     * message. Meaning:
     * - The link is the only part of the message body.
     * - There is only one link in the message body.
     * - The link preview is of image type.
     */
    get linkPreviewSquash() {
        return (
            this.store.hasLinkPreviewFeature &&
            this.body &&
            this.body.startsWith("<a") &&
            this.body.endsWith("/a>") &&
            this.body.match(/<\/a>/im)?.length === 1 &&
            this.message_link_preview_ids.length === 1 &&
            this.message_link_preview_ids[0].link_preview_id.isImage
        );
    }

    /**
     * This is the preferred way to display the name of the author of a message.
     */
    get authorName() {
        if (this.author) {
            return this.getPersonaName(this.author);
        }
        return this.email_from;
    }

    get notificationHidden() {
        return false;
    }

    inlineBody = fields.Html("", {
        /** @this {import("models").Message} */
        compute() {
            if (this.notificationType === "call") {
                return _t("%(caller)s started a call", { caller: this.authorName });
            }
            if (this.notificationType === "channel_rename") {
                const name = htmlToTextContentInline(this.body);
                const params = { user: this.authorName, name: markup`<b>${name}</b>` };
                return this.thread?.parent_channel_id
                    ? _t("%(user)s changed the thread name to %(name)s", params)
                    : _t("%(user)s changed the channel name to %(name)s", params);
            }
            if (this.isEmpty) {
                return _t("This message has been removed");
            }
            if (!this.body) {
                return "";
            }
            return decorateEmojis(htmlToTextContentInline(this.body));
        },
    });

    get notificationIcon() {
        switch (this.notificationType) {
            case "pin":
                return "fa fa-thumb-tack";
            case "call":
                return "fa fa-phone";
        }
        return null;
    }

    get failureNotifications() {
        return this.notification_ids.filter((notification) => notification.isFailure);
    }

    get scheduledDateSimple() {
        return this.scheduledDatetime.toLocaleString(DateTime.TIME_SIMPLE, {
            locale: user.lang,
        });
    }

    get canToggleStar() {
        return Boolean(
            !this.is_transient &&
                !this.isPending &&
                this.thread &&
                this.store.self_partner?.main_user_id?.share === false &&
                this.persistent
        );
    }

    get hasOnlyAttachments() {
        return this.isBodyEmpty && this.attachment_ids.length > 0;
    }

    previewText = fields.Html("", {
        /** @this {import("models").Message} */
        compute() {
            if (!this.hasOnlyAttachments) {
                return this.inlineBody || this.subtype_id?.description;
            }
            const { attachment_ids: attachments } = this;
            if (!attachments || attachments.length === 0) {
                return "";
            }
            switch (attachments.length) {
                case 1:
                    return attachments[0].previewName;
                case 2:
                    return _t("%(file1)s and %(file2)s", {
                        file1: attachments[0].previewName,
                        file2: attachments[1].previewName,
                        count: attachments.length - 1,
                    });
                default:
                    return _t("%(file1)s and %(count)s other attachments", {
                        file1: attachments[0].previewName,
                        count: attachments.length - 1,
                    });
            }
        },
    });

    get previewIcon() {
        const { attachment_ids: attachments } = this;
        if (!attachments || attachments.length === 0) {
            return "";
        }
        const firstAttachment = attachments[0];
        switch (true) {
            case firstAttachment.isImage:
                return "fa-picture-o";
            case firstAttachment.mimetype === "audio/mpeg":
                return firstAttachment.voice ? "fa-microphone" : "fa-headphones";
            case firstAttachment.isVideo:
                return "fa-video-camera";
            default:
                return "fa-file";
        }
    }

    /** @param {import("models").Thread} thread the thread where the message is shown */
    canAddReaction(thread) {
        return Boolean(
            !this.is_transient &&
                !this.isPending &&
                this.thread?.can_react &&
                !this.thread.isTransient
        );
    }

    /** @param {import("models").Thread} thread the thread where the message is shown */
    canReplyTo(thread) {
        return (
            ["discuss.channel", "mail.box"].includes(thread.model) &&
            this.message_type !== "user_notification"
        );
    }

    /** @param {import("models").Thread} thread the thread where the message is shown */
    canUnfollow(thread) {
        return Boolean(this.thread?.selfFollower && thread?.model === "mail.box");
    }

    async copyLink() {
        let notification = _t("Message Link Copied!");
        let type = "info";
        try {
            await browser.navigator.clipboard.writeText(url(`/mail/message/${this.id}`));
        } catch {
            notification = _t("Message Link Copy Failed (Permission denied?)!");
            type = "danger";
        }
        this.store.env.services.notification.add(notification, { type });
    }

    async copyMessageText() {
        const messageBody = convertBrToLineBreak(this.body);
        try {
            await browser.navigator.clipboard.writeText(messageBody);
        } catch {
            this.store.env.services.notification.add(
                _t("Message Copy Failed (Permission denied?)!"),
                { type: "danger" }
            );
        }
        this.store.env.services.notification.add(_t("Message Copied!"), { type: "info" });
    }

    async edit(
        body,
        attachments = [],
        { mentionedChannels = [], mentionedPartners = [], mentionedRoles = [] } = {}
    ) {
        if (convertBrToLineBreak(this.body) === body && attachments.length === 0) {
            return;
        }
        const validMentions = this.store.getMentionsFromText(body, {
            mentionedChannels,
            mentionedPartners,
            mentionedRoles,
        });
        const hadLink = this.hasLink; // to remove old previews if message no longer contains any link
        const updateData = {
            attachment_ids: attachments
                .concat(this.attachment_ids)
                .map((attachment) => attachment.id),
            attachment_tokens: attachments
                .concat(this.attachment_ids)
                .map((attachment) => attachment.ownership_token),
            body: await prettifyMessageContent(body, { validMentions }),
            partner_ids: validMentions?.partners?.map((partner) => partner.id),
            role_ids: validMentions?.roles?.map((role) => role.id),
        };
        this.store.fillPartnersMentionToken(updateData);
        const data = await rpc("/mail/message/update_content", {
            message_id: this.id,
            update_data: updateData,
            ...this.thread.rpcParams,
        });
        this.store.insert(data);
        if ((hadLink || this.hasLink) && this.store.hasLinkPreviewFeature) {
            rpc("/mail/link_preview", { message_id: this.id }, { silent: true });
        }
        return data;
    }

    /** @param {import("models").Thread} thread the thread where the message is being viewed when starting edition */
    enterEditMode(thread) {
        const text = convertBrToLineBreak(this.body);
        if (thread?.messageInEdition) {
            thread.messageInEdition.composer = undefined;
        }
        this.composer = {
            mentionedPartners: this.partner_ids,
            composerText: text,
            selection: {
                start: text.length,
                end: text.length,
                direction: "none",
            },
        };
    }

    /** @param {import("models").Thread} thread the thread where the message is being viewed when stopping edition */
    exitEditMode(thread) {
        const threadAsInEdition = this.threadAsInEdition;
        this.composer = undefined;
        if (threadAsInEdition && threadAsInEdition.eq(thread)) {
            threadAsInEdition.composer.autofocus++;
        }
    }

    /**
     * Provide fallback to displayName in the absence of a thread
     *
     * @param {import("models").Persona} persona
     * @returns {string}
     */
    getPersonaName(persona) {
        return this.thread?.getPersonaName(persona) || persona.displayName;
    }

    async react(content) {
        this.store.insert(
            await rpc(
                "/mail/message/reaction",
                {
                    action: "add",
                    content,
                    message_id: this.id,
                    ...this.thread.rpcParams,
                },
                { silent: true }
            )
        );
    }

    async remove({ removeFromThread = false } = {}) {
        const data = await rpc("/mail/message/update_content", {
            message_id: this.id,
            update_data: this.removeParams,
        });
        this.store.insert(data);
        if (this.thread && removeFromThread) {
            this.thread.messages = this.thread.messages.filter((message) => message.notEq(this));
        }
        this.composer = undefined;
        return data;
    }

    get removeParams() {
        return {
            attachment_ids: [],
            attachment_tokens: [],
            body: "",
            partner_ids: [],
        };
    }

    async setDone() {
        await this.store.env.services.orm.silent.call("mail.message", "set_message_done", [
            [this.id],
        ]);
    }

    async toggleStar() {
        this.store.insert(
            await this.store.env.services.orm.silent.call(
                "mail.message",
                "toggle_message_starred",
                [[this.id]]
            )
        );
    }

    async unfollow() {
        if (this.needaction) {
            await this.setDone();
        }
        const thread = this.thread;
        await thread.selfFollower.remove();
        this.store.env.services.notification.add(
            _t('You are no longer following "%(thread_name)s".', {
                thread_name: thread.display_name,
            }),
            { type: "success" }
        );
    }

    hideAllLinkPreviews() {
        rpc("/mail/link_preview/hide", {
            message_link_preview_ids: this.message_link_preview_ids.map((lpm) => lpm.id),
        });
    }
}

Message.register();
