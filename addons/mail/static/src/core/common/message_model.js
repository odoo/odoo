// @ts-check
/** @odoo-module native */
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import {
    getMentionsFromText,
    updatePartnersMentionToken,
} from "@mail/core/common/message_post";
import { fields, Record } from "@mail/core/common/record";
import { getPersonaName } from "@mail/core/common/thread_model";
import { applyCounterDelta, snapshotCounter } from "@mail/utils/common/counters";
import {
    convertBrToLineBreak,
    decorateEmojis,
    EMOJI_REGEX,
    generateEmojisOnHtml,
    getNonEditableMentions,
    htmlToTextContentInline,
} from "@mail/utils/common/format";
import { markup, toRaw } from "@odoo/owl";
import { loadEmoji } from "@web/components/emoji_picker";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { makeLogger } from "@web/core/debug/debug_logger";
import { luxon } from "@web/core/l10n/luxon";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import {
    createDocumentFragmentFromContent,
    createElementWithContent,
} from "@web/core/utils/dom/html";
import { url } from "@web/core/utils/urls";
const { DateTime } = luxon;

/** @type {WeakMap<Message, luxon.DateTime>} */
const fallbackDatetimes = new WeakMap();

/** @type {WeakMap<object, Document>} */
const parsedBodies = new WeakMap();
/** @param {string|ReturnType<markup>} body */
function parseBody(body) {
    if (!body || typeof body === "string") {
        return createDocumentFragmentFromContent(body || "");
    }
    let fragment = parsedBodies.get(body);
    if (!fragment) {
        fragment = createDocumentFragmentFromContent(body);
        parsedBodies.set(body, fragment);
    }
    return fragment;
}

const log = makeLogger("mail.message");

export class Message extends Record {
    static _name = "mail.message";
    static id = "id";

    /** @param {Object} data */
    update(data) {
        super.update(data);
        if (typeof this.id === "number" && this.store.deletedMessageIds?.has(this.id)) {
            log.logic("update of a deleted message", () => ({ id: this.id }));
            this.delete();
            return;
        }
        if (typeof this.id === "number" && this.id > this.store.lastKnownMessageId) {
            this.store.lastKnownMessageId = this.id;
        }
        if (this.isNotification && !this.notificationType) {
            const htmlBody = parseBody(this.body);
            this.notificationType = /** @type {HTMLElement|null} */ (
                htmlBody.querySelector(".o_mail_notification")
            )?.dataset.oeType;
        }
    }

    attachment_ids = fields.Many("ir.attachment", { inverse: "message" });
    author_id = fields.One("res.partner");
    author_guest_id = fields.One("mail.guest");
    get author() {
        return this.author_id || this.author_guest_id;
    }
    body = fields.Html("");
    isBodyEmpty = fields.Attr(undefined, {
        /** @this {import("models").Message} */
        compute() {
            return (
                !this.body || isEmptyBlock(createElementWithContent("div", this.body))
            );
        },
    });
    call_history_ids = fields.Many("discuss.call.history");
    richBody = fields.Html("", {
        /** @this {import("models").Message} */
        compute() {
            if (!this.store.emojiLoader.loaded) {
                loadEmoji();
            }
            return decorateEmojis(this.body) ?? "";
        },
    });
    richTranslationValue = fields.Html("", {
        /** @this {import("models").Message} */
        compute() {
            if (!this.store.emojiLoader.loaded) {
                loadEmoji();
            }
            return decorateEmojis(this.translationValue) ?? "";
        },
    });
    composer = fields.One("Composer", {
        inverse: "message",
        onDelete: (r) => r.delete(),
    });
    composerAsReplyToMessage = fields.One("Composer", { inverse: "replyToMessage" });
    date = fields.Datetime();
    /** @type {string} */
    default_subject;
    /** @type {boolean} */
    edited = fields.Attr(false, {
        /** @this {import("models").Message} */
        compute() {
            return Boolean(
                parseBody(this.body).querySelector(".o-mail-Message-edited"),
            );
        },
    });
    extra_body_attachment_ids = fields.Many("ir.attachment", {
        /** @this {import("models").Message} */
        compute() {
            const parsedBody = parseBody(this.body);
            const inlinedImageAttachmentIds = [
                .../** @type {NodeListOf<HTMLImageElement>} */ (
                    parsedBody.querySelectorAll("img[data-attachment-id]")
                ),
            ].map((img) => parseInt(img.dataset.attachmentId));

            return this.attachment_ids.filter(
                (a) => !inlinedImageAttachmentIds.includes(a.id),
            );
        },
    });
    hasLink = fields.Attr(false, {
        /** @this {import("models").Message} */
        compute() {
            if (this.isBodyEmpty) {
                return false;
            }
            return Boolean(
                parseBody(this.body).querySelector("a:not([data-oe-model])"),
            );
        },
    });
    hasMailNotificationSummary = fields.Attr(false, {
        /** @this {import("models").Message} */
        compute() {
            return Boolean(
                parseBody(this.body).querySelector('[summary="o_mail_notification"]'),
            );
        },
    });
    /** @type {number|string} */
    id;
    /** @type {string} */
    email_from;
    /** @type {string[][]} */
    incoming_email_cc;
    /** @type {string[][]} */
    incoming_email_to;
    get isDiscussion() {
        return this.store.mt_comment?.eq(this.subtype_id);
    }
    get isNote() {
        return this.store.mt_note?.eq(this.subtype_id);
    }
    /** @type {boolean} */
    is_transient;
    message_link_preview_ids = fields.Many("mail.message.link.preview", {
        inverse: "message_id",
    });
    /** @type {import("models").Message} */
    parent_id = fields.One("mail.message");
    /** @type {(() => Promise<void>)|undefined} */
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
        /** @this {import("models").Message} */
        compute() {
            if (this.needaction) {
                return this.thread;
            }
        },
    });
    threadAsNewest = fields.One("Thread");
    threadAsInEdition = fields.One("Thread", {
        /** @this {import("models").Message} */
        compute() {
            if (this.composer) {
                return this.thread;
            }
        },
    });
    scheduledDatetime = fields.Datetime();
    onlyEmojis = fields.Attr(false, {
        /** @this {import("models").Message} */
        compute() {
            const bodyWithoutTags = parseBody(this.body).body?.textContent ?? "";
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
    /** @type {string | import("@odoo/owl").Markup | undefined} */
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
    showTranslation = false;

    /** @returns {boolean} */
    get allowsEdition() {
        return this.store.selfIsAdmin || this.isSelfAuthored;
    }

    get bubbleColor() {
        if (this.message_type === "notification") {
            return undefined;
        }
        if (this.isHighlightedFromMention) {
            return "orange";
        }
        if (this.isNote) {
            return undefined;
        }
        return this.isSelfAuthored ? "green" : "blue";
    }

    get editable() {
        if (this.isEmpty || !this.allowsEdition) {
            return false;
        }
        return this.message_type === "comment";
    }

    get dateDay() {
        return this.datetime.hasSame(DateTime.now(), "day")
            ? _t("Today")
            : this.datetime.toLocaleString(DateTime.DATE_MED);
    }

    get dateSimple() {
        return this.datetime
            .toLocaleString(DateTime.TIME_SIMPLE, {
                locale: user.lang,
            })
            .replace(" ", " ");
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
                userLocale,
            );
        }
        return this.datetime.toLocaleString({ ...DateTime.DATETIME_MED }, userLocale);
    }

    get datetime() {
        if (this.date) {
            return this.date;
        }
        const raw = toRaw(this)._raw;
        let fallback = fallbackDatetimes.get(raw);
        if (!fallback) {
            fallback = DateTime.now();
            fallbackDatetimes.set(raw, fallback);
        }
        return fallback;
    }

    /** @returns {import("models").ResPartner|import("models").MailGuest} */
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
        return this.isSelfMentioned && this.thread?.isChannelKind;
    }

    isSelfAuthored = fields.Attr(false, {
        /** @this {import("models").Message} */
        compute() {
            return Boolean(this.author?.eq(this.effectiveSelf));
        },
    });

    isPending = false;

    get hasActions() {
        return !this.is_transient;
    }

    get isNotification() {
        return (
            this.message_type === "notification" && Boolean(this.thread?.isChannelKind)
        );
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
        const defaultSubject = this.default_subject
            ? this.default_subject.toLowerCase()
            : "";
        const candidates = new Set([defaultSubject, threadName]);
        return candidates.has(this.subject?.toLowerCase());
    }

    get persistent() {
        return Number.isInteger(this.id);
    }

    get resUrl() {
        return url(
            router.stateToUrl({ model: this.thread.model, resId: this.thread.id }),
        );
    }

    /**
     * @param {import("models").Thread} [thread]
     * @returns {boolean}
     */
    isTranslatable(thread) {
        return (
            !this.isEmpty &&
            !this.isBodyEmpty &&
            !this.hasMailNotificationSummary &&
            this.store.hasMessageTranslationFeature &&
            !(thread?.isChannelKind || thread?.isMailbox)
        );
    }

    get hasTextContent() {
        return !this.isBodyEmpty || this.subject || this.edited;
    }

    isEmpty = fields.Attr(false, {
        /** @this {import("models").Message} */
        compute() {
            return this.computeIsEmpty();
        },
    });

    computeIsEmpty() {
        return (
            this.isBodyEmpty &&
            this.attachment_ids.length === 0 &&
            this.trackingValues.length === 0 &&
            !this.subtype_id?.description &&
            !this.subject
        );
    }

    get linkPreviewSquash() {
        return (
            this.store.hasLinkPreviewFeature &&
            this.body &&
            this.body.startsWith("<a") &&
            this.body.endsWith("/a>") &&
            this.body.match(/<\/a>/gi)?.length === 1 &&
            this.message_link_preview_ids.length === 1 &&
            this.message_link_preview_ids[0].link_preview_id.isImage
        );
    }

    get authorName() {
        if (this.author) {
            return this.getPersonaName(this.author);
        }
        return this.email_from || _t("Unnamed");
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
            if (this.notificationType === "thread_deletion") {
                return _t('%(user)s deleted the thread "%(thread_name)s"', {
                    user: this.authorName,
                    thread_name: decorateEmojis(htmlToTextContentInline(this.body)),
                });
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
                return "fa-solid fa-thumbtack";
            case "call":
                return "fa-solid fa-phone";
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
        return this.persistent && this.store.selfIsInternalUser;
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
            switch (attachments.length) {
                case 1:
                    return attachments[0].previewName;
                case 2:
                    return _t("%(file1)s and %(file2)s", {
                        file1: attachments[0].previewName,
                        file2: attachments[1].previewName,
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
                return "fa-regular fa-image";
            case firstAttachment.mimetype === "audio/mpeg":
                return firstAttachment.voice
                    ? "fa-solid fa-microphone"
                    : "fa-solid fa-headphones";
            case firstAttachment.isVideo:
                return "fa-solid fa-video";
            default:
                return "fa-solid fa-file";
        }
    }

    canAddReaction() {
        return Boolean(
            this.persistent &&
            this.thread?.can_react &&
            !this.thread.isTransient &&
            this.thread.has_mail_thread,
        );
    }

    /** @param {import("models").Thread} thread */
    canReplyTo(thread) {
        return (
            (thread?.isChannelKind || thread?.isMailbox) &&
            this.message_type !== "user_notification"
        );
    }

    /** @param {import("models").Thread} thread */
    canUnfollow(thread) {
        return Boolean(this.thread?.selfFollower && thread?.isMailbox);
    }

    async copyLink() {
        await this._copyToClipboard(
            url(`/mail/message/${this.id}`),
            _t("Message Link Copied!"),
            _t("Message Link Copy Failed (Permission denied?)!"),
        );
    }

    async copyMessageText() {
        await this._copyToClipboard(
            convertBrToLineBreak(this.body),
            _t("Message Copied!"),
            _t("Message Copy Failed (Permission denied?)!"),
        );
    }

    /**
     * @param {string} text
     * @param {string} copiedNotification
     * @param {string} failedNotification
     */
    async _copyToClipboard(text, copiedNotification, failedNotification) {
        let notification = copiedNotification;
        /** @type {"info" | "danger"} */
        let type = "info";
        try {
            await browser.navigator.clipboard.writeText(text);
        } catch {
            notification = failedNotification;
            type = "danger";
        }
        log.logic("copyToClipboard", () => ({ id: this.id, type }));
        this.store.env.services.notification.add(notification, { type });
    }

    /**
     * @param {string|ReturnType<markup>} body
     * @param {import("models").Attachment[]} [attachments=[]]
     * @param {Object} [mentions]
     * @param {import("models").Thread[]} [mentions.mentionedChannels=[]]
     * @param {import("models").ResPartner[]} [mentions.mentionedPartners=[]]
     * @param {Object[]} [mentions.mentionedRoles=[]]
     */
    async edit(
        body,
        attachments = [],
        { mentionedChannels = [], mentionedPartners = [], mentionedRoles = [] } = {},
    ) {
        log.logic("edit", () => ({
            id: this.id,
            thread: this.thread?.localId,
            attachments: attachments.length,
        }));
        const messageBodyEl = createElementWithContent("div", this.body);
        const updatedBodyEl = createElementWithContent("div", body);
        messageBodyEl.querySelector("span.o-mail-Message-edited")?.remove();
        updatedBodyEl.querySelector("span.o-mail-Message-edited")?.remove();
        if (
            updatedBodyEl.innerHTML === messageBodyEl.innerHTML &&
            attachments.length === 0
        ) {
            return;
        }
        const validMentions = getMentionsFromText(this.store, body, {
            mentionedChannels,
            mentionedPartners,
            mentionedRoles,
            thread: this.thread,
        });
        const hadLink = this.hasLink;
        const allAttachments = attachments.concat(this.attachment_ids);
        const updateData = {
            attachment_ids: allAttachments.map((attachment) => attachment.id),
            attachment_tokens: allAttachments.map(
                (attachment) => attachment.ownership_token,
            ),
            body: await generateEmojisOnHtml(body),
            partner_ids: validMentions?.partners?.map((partner) => partner.id),
            role_ids: validMentions?.roles?.map((role) => role.id),
        };
        updatePartnersMentionToken(this.store, updateData);
        const data = await rpc("/mail/message/update_content", {
            message_id: this.id,
            update_data: updateData,
            ...this.thread?.rpcParams,
        });
        this.store.insert(data);
        if ((hadLink || this.hasLink) && this.store.hasLinkPreviewFeature) {
            rpc("/mail/link_preview", { message_id: this.id }, { silent: true });
        }
        return data;
    }

    /** @param {import("models").Thread} thread */
    async enterEditMode(thread) {
        log.lifecycle("enterEditMode", () => ({
            id: this.id,
            thread: thread?.localId,
        }));
        const doc = parseBody(this.body);
        const validChannels = (
            await Promise.all(
                Array.from(
                    /** @type {NodeListOf<HTMLAnchorElement>} */ (
                        doc.querySelectorAll(
                            ".o_channel_redirect[data-oe-model='discuss.channel']",
                        )
                    ),
                ).map(async (/** @type {HTMLElement} */ el) =>
                    this.store.Thread.getOrFetch({
                        id: Number(el.dataset.oeId),
                        model: "discuss.channel",
                    }),
                ),
            )
        ).filter((channel) => channel?.exists());
        const validRoles = Array.from(
            /** @type {NodeListOf<HTMLElement>} */ (
                doc.querySelectorAll(".o-discuss-mention[data-oe-model='res.role']")
            ),
        ).map((el) => this.store["res.role"].get(el.dataset.oeId));
        const text = convertBrToLineBreak(this.body);
        if (thread?.messageInEdition) {
            thread.messageInEdition.composer = undefined;
        }
        this.composer = /** @type {typeof this.composer} */ (
            /** @type {unknown} */ ({
                composerHtml: getNonEditableMentions(this.body),
                mentionedChannels: validChannels,
                mentionedPartners: this.partner_ids,
                mentionedRoles: validRoles,
                selection: {
                    start: text.length,
                    end: text.length,
                    direction: "none",
                },
            })
        );
    }

    /** @param {import("models").Thread} thread */
    exitEditMode(thread) {
        const threadAsInEdition = this.threadAsInEdition;
        log.lifecycle("exitEditMode", () => ({
            id: this.id,
            thread: thread?.localId,
            refocus: Boolean(threadAsInEdition && threadAsInEdition.eq(thread)),
        }));
        this.composer = undefined;
        if (threadAsInEdition && threadAsInEdition.eq(thread)) {
            threadAsInEdition.composer.autofocus++;
        }
    }

    /**
     * @param {import("models").ResPartner|import("models").MailGuest} persona
     * @returns {string}
     */
    getPersonaName(persona) {
        return (
            this.thread?.getPersonaName(persona) ||
            getPersonaName(persona) ||
            _t("Unnamed")
        );
    }

    async onClickToggleTranslation() {
        if (!this.translationValue) {
            const endTranslate = log.perf("translate");
            const { error, lang_name, body } = await rpc("/mail/message/translate", {
                message_id: this.id,
            });
            endTranslate({ id: this.id, lang: lang_name, error: Boolean(error) });
            this.translationValue = body && markup(body);
            this.translationSource = lang_name;
            this.translationErrors = error;
        }
        this.showTranslation = !this.showTranslation && Boolean(this.translationValue);
        log.logic("toggleTranslation", () => ({
            id: this.id,
            shown: this.showTranslation,
            source: this.translationSource,
        }));
    }

    /** @param {string} content */
    async react(content) {
        log.logic("react", () => ({ id: this.id, content }));
        this.store.insert(
            await rpc(
                "/mail/message/reaction",
                {
                    action: "add",
                    content,
                    message_id: this.id,
                    ...this.thread?.rpcParams,
                },
                { silent: true },
            ),
        );
    }

    /**
     * @param {Object} [options]
     * @param {boolean} [options.removeFromThread=false]
     */
    async remove({ removeFromThread = false } = {}) {
        log.logic("remove", () => ({
            id: this.id,
            thread: this.thread?.localId,
            removeFromThread,
        }));
        const data = await rpc("/mail/message/update_content", {
            message_id: this.id,
            update_data: this.removeParams,
            ...this.thread?.rpcParams,
        });
        this.store.insert(data);
        if (this.thread && removeFromThread) {
            this.thread.messages = /** @type {typeof this.thread.messages} */ (
                /** @type {unknown} */ (
                    this.thread.messages.filter((message) => message.notEq(this))
                )
            );
        }
        this.composer = undefined;
        return data;
    }

    /** @returns {import("@mail/core/common/message_post").MessagePostData} */
    get removeParams() {
        return {
            attachment_ids: [],
            attachment_tokens: [],
            body: "",
            subject: "",
            partner_ids: [],
        };
    }

    /** @this {import("models").Message} */
    async setDone() {
        const wasNeedaction = this.needaction;
        const inbox = this.store.inbox;
        const inboxSnapshot = inbox && snapshotCounter(inbox, "counter");
        const threadSnapshot =
            this.thread && snapshotCounter(this.thread, "message_needaction_counter");
        let inboxApplied = 0;
        let threadApplied = 0;
        log.logic("setDone", () => ({
            id: this.id,
            wasNeedaction,
            thread: this.thread?.localId,
        }));
        if (wasNeedaction) {
            this.needaction = false;
            if (inbox) {
                inbox.messages.delete(this);
                inboxApplied = applyCounterDelta(inbox, "counter", -1);
            }
            if (this.thread) {
                threadApplied = applyCounterDelta(
                    this.thread,
                    "message_needaction_counter",
                    -1,
                );
            }
        }
        try {
            await this.store.env.services.orm.silent.call(
                "mail.message",
                "set_message_done",
                [[this.id]],
            );
        } catch (e) {
            log.logic("setDone rollback", () => ({ id: this.id, wasNeedaction }));
            if (wasNeedaction) {
                this.needaction = true;
                if (inbox) {
                    inbox.messages.add(this);
                    inboxSnapshot.restoreDelta(-inboxApplied);
                }
                threadSnapshot?.restoreDelta(-threadApplied);
            }
            console.warn("Failed to mark message as read", e);
        }
    }

    async toggleStar() {
        log.logic("toggleStar", () => ({ id: this.id, starred: this.starred }));
        this.store.insert(
            await this.store.env.services.orm.silent.call(
                "mail.message",
                "toggle_message_starred",
                [[this.id]],
            ),
        );
    }

    /** @this {import("models").Message} */
    async unfollow() {
        log.logic("unfollow", () => ({
            id: this.id,
            thread: this.thread?.localId,
            needaction: this.needaction,
        }));
        if (this.needaction) {
            await this.setDone();
        }
        const thread = this.thread;
        await thread.selfFollower.remove();
        this.store.env.services.notification.add(
            _t('You are no longer following "%(thread_name)s".', {
                thread_name: thread.display_name,
            }),
            { type: "success" },
        );
    }

    hideAllLinkPreviews() {
        log.logic("hideAllLinkPreviews", () => ({
            id: this.id,
            previews: this.message_link_preview_ids.length,
        }));
        rpc("/mail/link_preview/hide", {
            message_link_preview_ids: this.message_link_preview_ids.map(
                (lpm) => lpm.id,
            ),
        });
    }
}

Message.register();
