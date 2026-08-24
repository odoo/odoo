import { isEmptyBlock } from "@html_editor/utils/dom_info";

import { fields, Record } from "@mail/model/export";
import {
    convertBrToLineBreak,
    decorateEmojis,
    EMOJI_REGEX,
    generateEmojisOnHtml,
    generateMentionElement,
    inlineElement,
    prepareBodyForEditing,
    htmlToTextContentInline,
} from "@mail/utils/common/format";
import { createElementFromContent, getInnerHtml, getOuterHtml } from "@mail/utils/common/html";

import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { createElementWithContent, htmlTrim } from "@web/core/utils/html";
import { renderToElement } from "@web/core/utils/render";
import { url } from "@web/core/utils/urls";

import { markup } from "@odoo/owl";
import { emojiLoader } from "@web/core/emoji_picker/emoji_loader";
import { discussComponentRegistry } from "./discuss_component_registry";

const { DateTime } = luxon;
export class Message extends Record {
    static _name = "mail.message";

    attachment_ids = fields.Many("ir.attachment", { inverse: "message" });
    author_id = fields.One("res.partner");
    author_guest_id = fields.One("mail.guest");
    get author() {
        return this.author_id || this.author_guest_id;
    }
    body = fields.Html("");
    /** Shared by every compute reading the body: clone it before modifying it. */
    bodyEl = this.computed(() => (this.body ? createElementFromContent(this.body) : null));
    call_history_ids = fields.Many("discuss.call.history");
    richBody = this.computed(() => {
        emojiLoader.load();
        if (!this.bodyEl) {
            return "";
        }
        return getInnerHtml(decorateEmojis(this.bodyEl.cloneNode(true)));
    });
    richTranslationValue = this.computed(() => {
        emojiLoader.load();
        if (!this.translationValue) {
            return "";
        }
        return getInnerHtml(decorateEmojis(createElementFromContent(this.translationValue)));
    });
    composer = fields.One("Composer", { inverse: "message", onDelete: (r) => r?.delete() });
    composerAsReplyToMessage = fields.One("Composer", { inverse: "replyToMessage" });
    date = fields.Datetime();
    /** @type {string} */
    default_subject;
    /** @type {string} */
    email_from;
    /** @type {boolean} */
    edited = this.computed(() =>
        Boolean(
            // ".o-mail-Message-edited" is the class added by the mail.thread in _message_update_content
            // when the message is edited
            this.bodyEl?.querySelector(".o-mail-Message-edited")
        )
    );
    editedDate = this.computed(() => {
        const editedDate = this.bodyEl?.querySelector(".o-mail-Message-edited")?.dataset.oDatetime;
        return editedDate ? deserializeDateTime(editedDate) : undefined;
    });
    /** attachments not already clearly visible in the body, unlike inlined images */
    extra_body_attachment_ids = fields.Many("ir.attachment", {
        compute() {
            const inlinedImageAttachmentIds = [
                ...(this.bodyEl?.querySelectorAll("img[data-attachment-id]") ?? []),
            ].map((img) => parseInt(img.dataset.attachmentId));

            return this.attachment_ids.filter((a) => !inlinedImageAttachmentIds.includes(a.id));
        },
    });
    hasLink = this.computed(() => {
        if (this.isBodyEmpty) {
            return false;
        }
        return Boolean(this.bodyEl?.querySelector("a:not([data-oe-model])"));
    });
    hasMailNotificationSummary = this.computed(() =>
        Boolean(this.bodyEl?.querySelector('[summary="o_mail_notification"]'))
    );
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
    /** @type {?boolean} */
    is_bookmarked;
    /** @type {boolean} */
    is_transient;
    message_link_preview_ids = fields.Many("mail.message.link.preview", { inverse: "message_id" });
    parent_id = fields.One("mail.message");
    /**
     * When set, this temporary/pending message failed message post, and the
     * value is a callback to re-attempt to post the message.
     *
     * @type {() => {} | undefined}
     */
    postFailRedo = undefined;
    reactions = fields.Many("MessageReactions", { inverse: "message" });
    sortedReactions = fields.Many("MessageReactions", {
        compute() {
            return [...this.reactions].sort((r1, r2) => r1.sequence - r2.sequence);
        },
    });
    notification_ids = fields.Many("mail.notification", { inverse: "mail_message_id" });
    self_notification = fields.One("mail.notification", {
        compute() {
            return this.notification_ids.find((n) =>
                n.res_partner_id?.eq(this.store.self_user?.partner_id)
            );
        },
    });
    partner_ids = fields.Many("res.partner");
    partner_cc_ids = fields.Many("res.partner");
    /** @type {string} */
    reply_to;
    subtype_id = fields.One("mail.message.subtype");
    thread = fields.One("mail.thread");
    threadAsNeedaction = fields.One("mail.thread", {
        compute() {
            if (this.needaction) {
                return this.thread;
            }
        },
    });
    threadAsNewest = fields.One("mail.thread");
    threadAsInEdition = fields.One("mail.thread", {
        compute() {
            if (this.composer) {
                return this.thread;
            }
        },
    });
    threadAsPinned = fields.One("mail.thread", {
        compute() {
            return this.pinned_at ? this.thread : undefined;
        },
        inverse: "pinnedMessages",
    });
    scheduledDatetime = fields.Datetime();
    onlyEmojis = this.computed(() => {
        const bodyWithoutTags = this.bodyEl?.textContent ?? "";
        const withoutEmojis = bodyWithoutTags.replace(EMOJI_REGEX, "");
        return (
            bodyWithoutTags.length > 0 &&
            bodyWithoutTags.match(EMOJI_REGEX) &&
            withoutEmojis.trim().length === 0
        );
    });
    pinned_at = fields.Datetime();
    /** @type {string} */
    subject;
    /** @type {Translation|undefined} */
    translationValue;
    /** @type {string|undefined} */
    translationSource;
    /** @type {string|undefined} */
    translationErrors;
    /** @type {string} */
    message_type;
    /** @type {string} model of the record the message is posted on */
    model;
    /** @type {string|undefined} */
    notificationType = this.computed(() => {
        if (!this.isNotification) {
            return undefined;
        }
        return this.bodyEl?.querySelector(".o_mail_notification")?.dataset.oeType;
    });
    channelAsThreadCreationNotification = fields.One("discuss.channel", {
        /** @this {import("models").Message} */
        compute() {
            if (this.notificationType !== "thread_creation") {
                return;
            }
            const channelId = this.bodyEl?.querySelector(".o_mail_notification")?.dataset.oeId;
            return channelId ? Number(channelId) : undefined;
        },
        inverse: "threadCreationMessages",
    });
    /** @type {string} display name of the record the message is posted on */
    record_name;
    /** @type {number} id of the record the message is posted on */
    res_id;
    create_date = fields.Datetime();
    write_date = fields.Datetime();
    /** @type {undefined|Boolean} */
    needaction;
    /** @type {undefined|Boolean} */
    needaction_done;
    showTranslation = false;
    ended_poll_ids = fields.Many("mail.poll", { inverse: "end_message_id" });
    started_poll_ids = fields.Many("mail.poll", { inverse: "start_message_id" });
    poll = fields.One("mail.poll", {
        compute() {
            return this.started_poll_ids[0] || this.ended_poll_ids[0];
        },
    });

    /**
     * True if the backend would technically allow edition
     * @returns {boolean}
     */
    get allowsEdition() {
        return this.store.self_user?.is_admin || this.isSelfAuthored;
    }

    get bubbleColor() {
        if (["notification", "tracking"].includes(this.message_type)) {
            return undefined;
        }
        if (this.isHighlightedFromMention) {
            return "orange";
        }
        if (!this.isSelfAuthored && !this.isNote) {
            return "blue";
        }
        if (this.isSelfAuthored && !this.isNote) {
            return "green";
        }
        return undefined;
    }

    get editable() {
        if (this.isEmpty || !this.allowsEdition || this.poll) {
            return false;
        }
        return this.message_type === "comment";
    }

    get deletable() {
        if (this.isEmpty || !this.allowsEdition) {
            return false;
        }
        return this.message_type === "comment";
    }

    get dateDay() {
        if (this.datetime.hasSame(this.store.startOfToday, "day")) {
            return _t("Today");
        }
        return this.datetime.toLocaleString(DateTime.DATE_MED);
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
        const startOfToday = this.store.startOfToday;
        if (this.datetime.hasSame(startOfToday, "day")) {
            return this.datetime.toLocaleString(DateTime.TIME_SIMPLE, userLocale);
        }
        if (this.datetime.hasSame(startOfToday.minus({ day: 1 }), "day")) {
            return _t("Yesterday at %(time)s", {
                time: this.datetime.toLocaleString(DateTime.TIME_SIMPLE, userLocale),
            });
        }
        if (this.datetime.hasSame(startOfToday, "year")) {
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

    get editedDatetimeMedium() {
        return this.editedDate?.toLocaleString({ ...DateTime.DATETIME_MED }, { locale: user.lang });
    }

    get editedText() {
        return _t("Last edited %(editedDate)s", { editedDate: this.editedDatetimeMedium });
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

    get datetimeMedium() {
        return this.datetime.toLocaleString({ ...DateTime.DATETIME_MED }, { locale: user.lang });
    }

    get isSelfMentioned() {
        return this.effectiveSelf.in(this.partner_ids);
    }

    get isHighlightedFromMention() {
        return this.isSelfMentioned && Boolean(this.thread?.channel);
    }

    isSelfAuthored = this.computed(() => Boolean(this.author?.eq(this.effectiveSelf)));

    isPending = false;

    get hasActions() {
        return !this.is_transient;
    }

    get isNotification() {
        return this.message_type === "notification" && this.thread?.channel;
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
        return url(router.stateToUrl({ model: this.thread.model, resId: this.thread.id }));
    }

    get isTranslatable() {
        return (
            !this.isEmpty &&
            !this.isBodyEmpty &&
            !this.hasMailNotificationSummary &&
            this.store.hasMessageTranslationFeature &&
            !this.channel_id
        );
    }

    get hasTextContent() {
        return !this.isBodyEmpty || this.subject || this.edited;
    }

    isEmpty = this.computed(() => this.computeIsEmpty());
    isBodyEmpty = this.computed(
        () => !this.body || isEmptyBlock(createElementWithContent("div", this.body))
    );

    computeIsEmpty() {
        return (
            this.isBodyEmpty &&
            this.attachment_ids.length === 0 &&
            !this.subtype_id?.description &&
            !this.poll &&
            !this.subject
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
        return this.email_from || _t("Unnamed");
    }

    get notificationHidden() {
        return false;
    }

    inlineBody = this.computed(() => {
        if (this.poll) {
            /** @type {Translation | undefined} */
            let text = this.poll.poll_question;
            if (this.ended_poll_ids.length) {
                text = this.poll.pollClosedText;
            }
            return markup`<i class="oi oi oi-fw o-me-0_5" data-icon="oi_view-cohort"></i>${text}`;
        }
        if (this.notificationType === "thread_deletion") {
            const nameEl = createElementFromContent(htmlToTextContentInline(this.body));
            return _t('%(user)s deleted the thread "%(thread_name)s"', {
                user: this.authorName,
                thread_name: getInnerHtml(decorateEmojis(nameEl)),
            });
        }
        if (this.notificationType === "channel_rename") {
            const name = htmlToTextContentInline(this.body);
            const params = { user: this.authorName, name: markup`<b>${name}</b>` };
            return this.thread?.channel?.parent_channel_id
                ? _t("%(user)s changed the thread name to %(name)s", params)
                : _t("%(user)s changed the channel name to %(name)s", params);
        }
        if (this.notificationType === "thread_creation") {
            const threadChannel = this.channelAsThreadCreationNotification;
            const threadLink = generateMentionElement({
                className: "o_channel_redirect",
                id: Number(threadChannel?.id),
                model: "discuss.channel",
                text: threadChannel?.displayName ?? _t("New Thread"),
            });
            return getOuterHtml(
                renderToElement("mail.Message.threadCreationNotification", {
                    threadCreationPrefix: _t("%(user)s started a thread: ", {
                        user: this.authorName,
                    }),
                    threadLink: getOuterHtml(threadLink),
                })
            );
        }
        if (this.isEmpty) {
            return _t("This message has been removed");
        }
        if (!this.bodyEl) {
            return "";
        }
        const bodyEl = this.bodyEl.cloneNode(true);
        return htmlTrim(getInnerHtml(decorateEmojis(inlineElement(bodyEl))));
    });

    get notificationIcon() {
        switch (this.notificationType) {
            case "pin":
                return "push_pin";
            case "call":
                return "phone";
        }
        return null;
    }

    failureNotifications = this.computed(() =>
        this.notification_ids.filter((notification) => notification.isFailure)
    );

    get scheduledDateSimple() {
        return this.scheduledDatetime.toLocaleString(DateTime.TIME_SIMPLE, {
            locale: user.lang,
        });
    }

    get canToggleBookmark() {
        return Boolean(
            !this.is_transient &&
                !this.isPending &&
                this.store.self_user?.share === false &&
                this.persistent
        );
    }

    get hasAttachments() {
        return this.attachment_ids?.length > 0;
    }

    get hasOnlyAttachments() {
        return this.isBodyEmpty && this.hasAttachments;
    }

    bodyPreview = this.computed(() => {
        /** @type {Translation} */
        let messageBody = "";
        if (!this.hasOnlyAttachments) {
            return this.inlineBody || this.subtype_id?.description;
        }
        const attachments = this.attachment_ids;
        switch (attachments.length) {
            case 1:
                messageBody = attachments[0].previewName;
                break;
            case 2:
                messageBody = _t("%(file1)s and %(file2)s", {
                    file1: attachments[0].previewName,
                    file2: attachments[1].previewName,
                    count: attachments.length - 1,
                });
                break;
            default:
                messageBody = _t("%(file1)s and %(count)s other attachments", {
                    file1: attachments[0].previewName,
                    count: attachments.length - 1,
                });
        }
        return markup`<i class="oi me-1" data-icon="${this.previewIcon}"></i>${messageBody}`;
    });

    previewText = fields.Html("", {
        /** @this {import("models").Message} */
        compute() {
            const messageBody = this.bodyPreview;
            if (this.isSelfAuthored) {
                return markup`<i class="oi me-1 opacity-75" data-icon="reply"></i>${_t(
                    "You: %(message_content)s",
                    { message_content: messageBody }
                )}`;
            }
            if (!this.author || this.author.notEq(this.thread?.channel?.correspondent?.persona)) {
                return _t("%(authorName)s: %(message_content)s", {
                    authorName: this.authorName,
                    message_content: messageBody,
                });
            }
            return messageBody;
        },
    });

    get previewIcon() {
        const { attachment_ids: attachments } = this;
        if (!this.hasAttachments) {
            return "";
        }
        const firstAttachment = attachments[0];
        switch (true) {
            case firstAttachment.isImage:
                return "image";
            case firstAttachment.mimetype === "audio/mpeg":
                return firstAttachment.voice ? "mic" : "headphones";
            case firstAttachment.isVideo:
                return "videocam";
            default:
                return "description";
        }
    }

    get canAddReaction() {
        return Boolean(
            !this.is_transient &&
                !this.isPending &&
                this.thread?.can_react &&
                !this.thread.isTransient &&
                this.thread.has_mail_thread
        );
    }

    get canMarkAsUnread() {
        return (
            !this.isEmpty &&
            !this.needaction &&
            !this.thread?.channel &&
            this.self_notification?.notification_type === "inbox"
        );
    }

    get canReplyTo() {
        return (
            this.thread?.channel &&
            !this.isEmpty &&
            this.message_type !== "user_notification" &&
            !this.thread.channel?.composerHidden
        );
    }

    get authorAvatarUrl() {
        if (
            this.message_type &&
            this.message_type.includes("email") &&
            !this.author_id &&
            !this.author_guest_id
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }
        if (this.author) {
            return this.author.avatarUrl;
        }
        return this.store.DEFAULT_AVATAR;
    }

    async copyLink() {
        let notification = _t("Message Link Copied");
        let type = "success";
        try {
            await browser.navigator.clipboard.writeText(url(`/mail/message/${this.id}`));
        } catch {
            notification = _t("Message Link Copy Failed (Permission denied?)");
            type = "danger";
        }
        this.store.env.services.notification.add(notification, { type });
    }

    get canCopyMessageText() {
        return !this.isBodyEmpty;
    }

    async copyMessageText() {
        const messageBody = convertBrToLineBreak(this.body);
        try {
            await browser.navigator.clipboard.writeText(messageBody);
        } catch {
            this.store.env.services.notification.add(_t("Text Copy Failed (Permission denied?)"), {
                type: "danger",
            });
        }
        this.store.env.services.notification.add(_t("Text copied"), { type: "success" });
    }

    /**
     * Edit the message body and/or its attachments
     *
     * @param {string} body - New HTML body content for the message.
     * @param {import("models").Attachment[]} [attachments=[]] - Attachments to keep on the message after the edit.
     * @param {Object} [options={}]
     * @param {import("models").ResPartner[]} [options.mentionedPartners=[]] - Partners mentioned in the new body.
     * @param {import("models").ResRole[]} [options.mentionedRoles=[]] - Roles mentioned in the new body.
     * @returns {Promise<Object|undefined>} The store-insert data returned by the server, or
     *   `undefined` if the edit was a no-op (body and attachments unchanged).
     */
    async edit(body, attachments = [], { mentionedPartners = [], mentionedRoles = [] } = {}) {
        const messageBodyEl = createElementWithContent("div", this.body);
        const updatedBodyEl = createElementWithContent("div", body);
        messageBodyEl.querySelector("span.o-mail-Message-edited")?.remove();
        updatedBodyEl.querySelector("span.o-mail-Message-edited")?.remove();
        if (
            updatedBodyEl.innerHTML === messageBodyEl.innerHTML &&
            attachments.length === this.attachment_ids.length &&
            attachments.every(
                (attachment, index) => attachment.id === this.attachment_ids[index].id
            )
        ) {
            return;
        }
        const validMentions = this.store.getMentionsFromText(body, {
            mentionedPartners,
            mentionedRoles,
            thread: this.thread,
        });
        const hadLink = this.hasLink; // to remove old previews if message no longer contains any link
        const updateData = {
            attachment_ids: attachments.map((attachment) => attachment.id),
            attachment_tokens: attachments.map((attachment) => attachment.ownership_token),
            body: await generateEmojisOnHtml(body),
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

    enterEditMode() {
        const validRoles = Array.from(
            this.bodyEl?.querySelectorAll(".o-discuss-mention[data-oe-model='res.role']") ?? []
        ).map((el) => this.store["res.role"].get(el.dataset.oeId));
        const text = convertBrToLineBreak(this.body);
        if (this.thread?.messageInEdition) {
            this.thread.messageInEdition.composer = undefined;
        }
        this.composer = {
            attachments: [...this.attachment_ids],
            composerHtml: prepareBodyForEditing(this.body),
            isEditComposerVisible: true,
            mentionedPartners: this.partner_ids,
            mentionedRoles: validRoles,
            selection: {
                start: text.length,
                end: text.length,
                direction: "none",
            },
        };
    }

    exitEditMode() {
        const threadAsInEdition = this.threadAsInEdition;
        this.composer = undefined;
        if (threadAsInEdition) {
            threadAsInEdition.composer.autofocus++;
        }
    }

    /**
     * @param {Object} owner
     * @param {import("@odoo/owl").Signal<HTMLElement>} [rootRef]
     */
    showDeleteConfirm(owner, rootRef) {
        this.store.env.services.dialog.add(
            discussComponentRegistry.get("MessageDeleteDialog"),
            { message: this, onConfirm: () => this.onShowDeleteConfirm(owner) },
            { rootRef }
        );
    }

    /**
     * @param {Object} owner
     * @param {import("@web/env").OdooEnv} owner.env
     */
    onShowDeleteConfirm(owner) {
        this.remove({ removeFromThread: this.shouldHideFromMessageListOnDelete(owner.env) });
    }

    /**
     * Provide fallback to displayName in the absence of a thread
     *
     * @param {import("models").Persona} persona
     * @returns {string}
     */
    getPersonaName(persona) {
        return (
            this.thread?.getPersonaName(persona) ||
            persona?.displayName ||
            persona?.name ||
            _t("Unnamed")
        );
    }
    async markAsUnread() {
        await this.store.env.services.orm.silent.call("mail.message", "mark_as_unread", [
            [this.id],
        ]);
        this.store.env.services.notification.add(_t("Marked as unread"), { type: "info" });
    }

    async toggleTranslation() {
        if (!this.translationValue) {
            const resp = await rpc("/mail/message/translate", { message_id: this.id });
            if (!resp) {
                return;
            }
            const { error, lang_name, body } = resp;
            this.translationValue = body && markup(body);
            this.translationSource = lang_name;
            this.translationErrors = error;
        }
        this.showTranslation = !this.showTranslation && Boolean(this.translationValue);
    }
    afterToggleTranslation() {
        if (!this.thread?.channel || this.thread.autoTranslateEnabled === this.showTranslation) {
            return;
        }
        const closeNotification = this.store.env.services.notification.add(
            this.showTranslation
                ? _t("Auto-translate future messages?")
                : _t("Cancel auto-translate?"),
            {
                type: "info",
                buttons: [
                    {
                        name: this.showTranslation ? _t("Enable") : _t("Disable"),
                        onClick: () => {
                            this.thread.autoTranslateEnabled = this.showTranslation;
                            closeNotification();
                        },
                        primary: true,
                    },
                ],
            }
        );
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
        let data;
        if (this.poll) {
            await rpc("/mail/poll/delete", { poll_id: this.poll.id });
        } else {
            data = await rpc("/mail/message/update_content", {
                message_id: this.id,
                update_data: this.removeParams,
                ...this.thread.rpcParams,
            });
            this.store.insert(data);
        }
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
            subject: "",
            partner_ids: [],
        };
    }

    async setDone() {
        await this.store.env.services.orm.silent.call("mail.message", "set_message_done", [
            [this.id],
        ]);
    }

    shouldHideFromMessageListOnDelete(env) {
        return false;
    }

    async addBookmark() {
        await this.store.fetchStoreData("add_bookmark", { message_id: this.id });
    }

    /** @param {import("@web/env").OdooEnv} env */
    async removeBookmark(env) {
        await this.store.fetchStoreData("remove_bookmark", { message_id: this.id });
        if (!env.inMessagingMenu) {
            return;
        }
        this.closeNotificationFn?.();
        this.closeNotificationFn = this.store.env.services.notification.add(
            _t("Bookmark removed"),
            {
                type: "success",
                buttons: [
                    {
                        name: "Undo",
                        icon: "undo",
                        onClick: async () => {
                            await this.addBookmark();
                            this.closeNotificationFn();
                        },
                    },
                ],
            }
        );
    }

    async unfollow() {
        const thread = this.thread;
        if (this.needaction) {
            await thread.markAllMessagesAsRead();
        }
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
