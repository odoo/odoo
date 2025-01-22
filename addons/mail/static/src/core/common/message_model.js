import { Record } from "@mail/core/common/record";
import {
    EMOJI_REGEX,
    convertBrToLineBreak,
    htmlToTextContentInline,
    prettifyMessageContent,
} from "@mail/utils/common/format";
import { rpc } from "@web/core/network/rpc";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { url } from "@web/core/utils/urls";
import { stateToUrl } from "@web/core/browser/router";
import { toRaw } from "@odoo/owl";

const { DateTime } = luxon;
export class Message extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Message>} */
    static records = {};
    /** @returns {import("models").Message} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Message|import("models").Message[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @param {Object} data */
    update(data) {
        super.update(data);
        if (this.isNotification && !this.notificationType) {
            const parser = new DOMParser();
            const htmlBody = parser.parseFromString(this.body, "text/html");
            this.notificationType = htmlBody.querySelector(".o_mail_notification")?.dataset.oeType;
        }
    }

    attachment_ids = Record.many("Attachment", { inverse: "message" });
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
                new DOMParser()
                    .parseFromString(this.body, "text/html")
                    // ".o-mail-Message-edited" is the class added by the mail.thread in _message_update_content
                    // when the message is edited
                    .querySelector(".o-mail-Message-edited")
            );
        },
    });
    hasEveryoneSeen = Record.attr(false, {
        /** @this {import("models").Message} */
        compute() {
            return this.thread?.membersThatCanSeen.every((m) => m.hasSeen(this));
        },
    });
    isMessagePreviousToLastSelfMessageSeenByEveryone = Record.attr(false, {
        /** @this {import("models").Message} */
        compute() {
            if (!this.thread?.lastSelfMessageSeenByEveryone) {
                return false;
            }
            return this.id < this.thread.lastSelfMessageSeenByEveryone.id;
        },
    });
    isReadBySelf = Record.attr(false, {
        compute() {
            return (
                this.thread?.selfMember?.seen_message_id?.id >= this.id &&
                this.thread?.selfMember?.new_message_separator > this.id
            );
        },
    });
    hasSomeoneSeen = Record.attr(false, {
        /** @this {import("models").Message} */
        compute() {
            return this.thread?.membersThatCanSeen
                .filter(({ persona }) => !persona.eq(this.author))
                .some((m) => m.hasSeen(this));
        },
    });
    hasSomeoneFetched = Record.attr(false, {
        /** @this {import("models").Message} */
        compute() {
            if (!this.thread) {
                return false;
            }
            const otherFetched = this.thread.channelMembers.filter(
                (m) => m.persona.notEq(this.author) && m.fetched_message_id?.id >= this.id
            );
            return otherFetched.length > 0;
        },
    });
    hasLink = Record.attr(false, {
        compute() {
            if (this.isBodyEmpty) {
                return false;
            }
            const div = document.createElement("div");
            div.innerHTML = this.body;
            return Boolean(div.querySelector("a:not([data-oe-model])"));
        },
    });
    /** @type {number|string} */
    id;
    /** @type {boolean} */
    is_discussion;
    /** @type {boolean} */
    is_note;
    /** @type {boolean} */
    is_transient;
    linkPreviews = Record.many("LinkPreview", { inverse: "message", onDelete: (r) => r.delete() });
    /** @type {number[]} */
    parentMessage = Record.one("Message");
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
    notifications = Record.many("Notification", { inverse: "message" });
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
    /** @type {DateTime} */
    scheduledDatetime = Record.attr(undefined, { type: "datetime" });
    onlyEmojis = Record.attr(false, {
        compute() {
            const div = document.createElement("div");
            div.innerHTML = this.body;
            const bodyWithoutTags = div.textContent;
            const withoutEmojis = bodyWithoutTags.replace(EMOJI_REGEX, "");
            return bodyWithoutTags.length > 0 && withoutEmojis.trim().length === 0;
        },
    });
    /** @type {string} */
    subject;
    /** @type {string} */
    subtype_description;
    threadAsFirstUnread = Record.one("Thread", { inverse: "firstUnreadMessage" });
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
        if (!this.allowsEdition) {
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
        return this.datetime.toLocaleString(DateTime.TIME_24_SIMPLE, {
            locale: user.lang,
        });
    }

    get dateSimpleWithDay() {
        const userLocale = { locale: user.lang };
        if (this.datetime.hasSame(DateTime.now(), "day")) {
            return _t("Today at %(time)s", {
                time: this.datetime.toLocaleString(DateTime.TIME_24_SIMPLE, userLocale),
            });
        }
        if (this.datetime.hasSame(DateTime.now().minus({ day: 1 }), "day")) {
            return _t("Yesterday at %(time)s", {
                time: this.datetime.toLocaleString(DateTime.TIME_24_SIMPLE, userLocale),
            });
        }
        if (this.datetime?.year === DateTime.now().year) {
            return this.datetime.toLocaleString(
                { ...DateTime.DATETIME_MED, hourCycle: "h23", year: undefined },
                userLocale
            );
        }
        return this.datetime.toLocaleString(
            { ...DateTime.DATETIME_MED, hourCycle: "h23" },
            userLocale
        );
    }

    get datetime() {
        return this.date || DateTime.now();
    }

    get datetimeShort() {
        return this.datetime.toLocaleString(DateTime.DATETIME_SHORT_WITH_SECONDS);
    }

    get isSelfMentioned() {
        return this.store.self.in(this.recipients);
    }

    get isHighlightedFromMention() {
        return this.isSelfMentioned && this.thread?.model === "discuss.channel";
    }

    isSelfAuthored = Record.attr(false, {
        compute() {
            if (!this.author) {
                return false;
            }
            return this.author.eq(this.store.self);
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
        if (!this.subject || !this.thread || !this.thread.name) {
            return false;
        }
        const regexPrefix = /^((re|fw|fwd)\s*:\s*)*/i;
        const cleanedThreadName = this.thread.name.replace(regexPrefix, "");
        const cleanedSubject = this.subject.replace(regexPrefix, "");
        return cleanedSubject === cleanedThreadName;
    }

    get isSubjectDefault() {
        const name = this.thread?.name;
        const threadName = name ? name.trim().toLowerCase() : "";
        const defaultSubject = this.default_subject ? this.default_subject.toLowerCase() : "";
        const candidates = new Set([defaultSubject, threadName]);
        return candidates.has(this.subject?.toLowerCase());
    }

    get resUrl() {
        return url(stateToUrl({ model: this.thread.model, resId: this.thread.id }));
    }

    isTranslatable(thread) {
        return (
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
                ["", "<p></p>", "<p><br></p>", "<p><br/></p>"].includes(
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
            this.linkPreviews.length === 1 &&
            this.linkPreviews[0].isImage
        );
    }

    get inlineBody() {
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
        return this.notifications.filter((notification) => notification.isFailure);
    }

    get scheduledDateSimple() {
        return this.scheduledDatetime.toLocaleString(DateTime.TIME_24_SIMPLE, {
            locale: user.lang,
        });
    }

    get canToggleStar() {
        return Boolean(
            !this.is_transient &&
                this.thread &&
                this.store.self.type === "partner" &&
                this.store.self.isInternalUser
        );
    }

    /** @param {import("models").Thread} thread the thread where the message is shown */
    canAddReaction(thread) {
        return Boolean(!this.is_transient && this.thread);
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
        await this.store.env.services.orm.silent.call("mail.message", "toggle_message_starred", [
            [this.id],
        ]);
    }

    async unfollow() {
        if (this.needaction) {
            await this.setDone();
        }
        const thread = this.thread;
        await thread.selfFollower.remove();
        this.store.env.services.notification.add(
            _t('You are no longer following "%(thread_name)s".', { thread_name: thread.name }),
            { type: "success" }
        );
    }

    get channelMemberHaveSeen() {
        return this.thread.membersThatCanSeen.filter(
            (m) => m.hasSeen(this) && m.persona.notEq(this.author)
        );
    }

    /** @param {import("models").Thread} thread the thread where the message is shown */
    onClickMarkAsUnread(thr) {
        const message = toRaw(this);
        const thread = toRaw(thr);
        if (!thread.selfMember || thread.selfMember?.new_message_separator === message.id) {
            return;
        }
        return rpc("/discuss/channel/mark_as_unread", {
            channel_id: message.thread.id,
            message_id: message.id,
        });
    }
}

Message.register();
