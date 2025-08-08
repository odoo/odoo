import { Record } from "@mail/core/common/record";
import {
    EMOJI_REGEX,
    convertBrToLineBreak,
    htmlToTextContentInline,
    prettifyMessageContent,
} from "@mail/utils/common/format";
import { createDocumentFragmentFromContent } from "@mail/utils/common/html";

import { browser } from "@web/core/browser/browser";
import { stateToUrl } from "@web/core/browser/router";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { setElementContent } from "@web/core/utils/html";
import { url } from "@web/core/utils/urls";

const { DateTime } = luxon;
export class Message extends Record {
    static _name = "mail.message";
    static id = "id";
    /** @type {Object.<number, import("models").Message>} */
    static records = {};
    /** @returns {import("models").Message} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @template T
     * @param {T} data
     * @returns {T extends any[] ? import("models").Message[] : import("models").Message}
     */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @param {Object} data */
    update(data) {
        super.update(data);
        if (this.isNotification && !this.notificationType) {
            const htmlBody = createDocumentFragmentFromContent(this.body);
            this.notificationType = htmlBody.querySelector(".o_mail_notification")?.dataset.oeType;
        }
    }

    attachment_ids = Record.many("ir.attachment", { inverse: "message" });
    author = Record.one("Persona");
    body = Record.attr("", { html: true });
    composer = Record.one("Composer", { inverse: "message", onDelete: (r) => r.delete() });
    /** @type {DateTime} */
    date = Record.attr(undefined, { type: "datetime" });
    /** @type {string} */
    default_subject;
    /** @type {boolean} */
    edited = Record.attr(false, {
        compute() {
            return Boolean(
                // ".o-mail-Message-edited" is the class added by the mail.thread in _message_update_content
                // when the message is edited
                createDocumentFragmentFromContent(this.body).querySelector(".o-mail-Message-edited")
            );
        },
    });
    hasLink = Record.attr(false, {
        compute() {
            if (this.isBodyEmpty) {
                return false;
            }
            const div = document.createElement("div");
            setElementContent(div, this.body);
            return Boolean(div.querySelector("a:not([data-oe-model])"));
        },
    });
    /** @type {number|string} */
    id;
    /** @type {Array[Array[string]]} */
    incoming_email_cc;
    /** @type {Array[Array[string]]} */
    incoming_email_to;
    /** @type {boolean} */
    is_discussion;
    /** @type {boolean} */
    is_note;
    /** @type {boolean} */
    is_transient;
    link_preview_ids = Record.many("mail.link.preview", {
        inverse: "message_id",
        onDelete: (r) => r.delete(),
    });
    /** @type {number[]} */
    parentMessage = Record.one("mail.message");
    /**
     * When set, this temporary/pending message failed message post, and the
     * value is a callback to re-attempt to post the message.
     *
     * @type {() => {} | undefined}
     */
    postFailRedo = undefined;
    reactions = Record.many("MessageReactions", {
        inverse: "message",
        /**
         * @param {import("models").MessageReactions} r1
         * @param {import("models").MessageReactions} r2
         */
        sort: (r1, r2) => r1.sequence - r2.sequence,
    });
    notification_ids = Record.many("mail.notification", { inverse: "mail_message_id" });
    recipients = Record.many("Persona");
    thread = Record.one("Thread");
    threadAsNeedaction = Record.one("Thread", {
        compute() {
            if (this.needaction) {
                return this.thread;
            }
        },
    });
    threadAsNewest = Record.one("Thread");
    threadAsInEdition = Record.one("Thread", {
        compute() {
            if (this.composer) {
                return this.thread;
            }
        },
    });
    /** @type {DateTime} */
    scheduledDatetime = Record.attr(undefined, { type: "datetime" });
    onlyEmojis = Record.attr(false, {
        compute() {
            const div = document.createElement("div");
            setElementContent(div, this.body);
            const bodyWithoutTags = div.textContent;
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
    /** @type {string} */
    subtype_description;
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
    /** @type {luxon.DateTime} */
    create_date = Record.attr(undefined, { type: "datetime" });
    /** @type {luxon.DateTime} */
    write_date = Record.attr(undefined, { type: "datetime" });
    /** @type {undefined|Boolean} */
    needaction;
    starred = false;

    /**
     * True if the backend would technically allow edition
     * @returns {boolean}
     */
    get allowsEdition() {
        return this.store.self.isAdmin || this.isSelfAuthored;
    }

    get bubbleColor() {
        if (this.message_type === "notification") {
            return undefined;
        }
        if (!this.isSelfAuthored && !this.is_note && !this.isHighlightedFromMention) {
            return "blue";
        }
        if (this.isSelfAuthored && !this.is_note && !this.isHighlightedFromMention) {
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

    /**
     * Get the current user's active identities.These identities include both
     * the cookie-authenticated persona and the partner authenticated with the
     * portal token in the context of the related thread.
     *
     * @deprecated
     * @returns {import("models").Persona[]}
     */
    get selves() {
        return this.thread?.selves ?? [this.store.self];
    }

    get datetimeShort() {
        return this.datetime.toLocaleString(DateTime.DATETIME_SHORT_WITH_SECONDS);
    }

    get isSelfMentioned() {
        return this.effectiveSelf.in(this.recipients);
    }

    get isHighlightedFromMention() {
        return this.isSelfMentioned && this.thread?.model === "discuss.channel";
    }

    isSelfAuthored = Record.attr(false, {
        compute() {
            if (!this.author) {
                return false;
            }
            return this.author.eq(this.effectiveSelf);
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

    isEmpty = Record.attr(false, {
        /** @this {import("models").Message} */
        compute() {
            return (
                this.isBodyEmpty &&
                this.attachment_ids.length === 0 &&
                this.trackingValues.length === 0 &&
                !this.subtype_description
            );
        },
    });
    isBodyEmpty = Record.attr(undefined, {
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
            this.link_preview_ids.length === 1 &&
            this.link_preview_ids[0].isImage
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

    get inlineBody() {
        if (this.isEmpty) {
            return _t("This message has been removed");
        }
        if (!this.body) {
            return "";
        }
        return htmlToTextContentInline(this.body);
    }

    get notificationIcon() {
        switch (this.notificationType) {
            case "pin":
                return "fa fa-thumb-tack";
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
                this.store.self.type === "partner" &&
                this.store.self.isInternalUser &&
                this.persistent
        );
    }

    /** @param {import("models").Thread} thread the thread where the message is shown */
    canAddReaction(thread) {
        return Boolean(!this.is_transient && !this.isPending && this.thread?.can_react);
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

    async edit(body, attachments = [], { mentionedChannels = [], mentionedPartners = [] } = {}) {
        if (convertBrToLineBreak(this.body) === body && attachments.length === 0) {
            return;
        }
        const validMentions = this.store.getMentionsFromText(body, {
            mentionedChannels,
            mentionedPartners,
        });
        const data = await rpc("/mail/message/update_content", {
            attachment_ids: attachments
                .concat(this.attachment_ids)
                .map((attachment) => attachment.id),
            attachment_tokens: attachments
                .concat(this.attachment_ids)
                .map((attachment) => attachment.access_token),
            body: await prettifyMessageContent(body, validMentions),
            message_id: this.id,
            partner_ids: validMentions?.partners?.map((partner) => partner.id),
            ...this.thread.rpcParams,
        });
        this.store.insert(data, { html: true });
        if (this.hasLink && this.store.hasLinkPreviewFeature) {
            rpc("/mail/link_preview", { message_id: this.id }, { silent: true });
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

    async remove() {
        await rpc("/mail/message/update_content", {
            attachment_ids: [],
            attachment_tokens: [],
            body: "",
            message_id: this.id,
            partner_ids: [],
            ...this.thread.rpcParams,
        });
        this.body = "";
        this.attachment_ids = [];
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
}

Message.register();
