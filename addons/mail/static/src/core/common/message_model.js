import { Record } from "@mail/core/common/record";
import {
    EMOJI_REGEX,
    convertBrToLineBreak,
    htmlToTextContentInline,
    prettifyMessageContent,
} from "@mail/utils/common/format";
import { rpc } from "@web/core/network/rpc";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { omit } from "@web/core/utils/objects";
import { url } from "@web/core/utils/urls";

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

    attachments = Record.many("Attachment", { inverse: "message" });
    author = Record.one("Persona");
    body = Record.attr("", { html: true });
    composer = Record.one("Composer", { inverse: "message", onDelete: (r) => r.delete() });
    /** @type {DateTime} */
    date = Record.attr(undefined, { type: "datetime" });
    /** @type {string} */
    default_subject;
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
    reactions = Record.many("MessageReactions", { inverse: "message" });
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
     * We exclude the milliseconds because datetime string from the server don't
     * have them. Message without date like transient message can be missordered
     */
    now = DateTime.now().set({ milliseconds: 0 });

    /**
     * True if the backend would technically allow edition
     * @returns {boolean}
     */
    get allowsEdition() {
        return this.store.self.isAdmin || this.isSelfAuthored;
    }

    get editable() {
        if (!this.allowsEdition) {
            return false;
        }
        return this.message_type === "comment";
    }

    get dateDay() {
        let dateDay = this.datetime.toLocaleString(DateTime.DATE_FULL);
        if (dateDay === DateTime.now().toLocaleString(DateTime.DATE_FULL)) {
            dateDay = _t("Today");
        }
        return dateDay;
    }

    get dateSimple() {
        return this.datetime.toLocaleString(DateTime.TIME_24_SIMPLE, {
            locale: user.lang?.replace("_", "-"),
        });
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
        // FIXME necessary to not trigger double-rendering of messages
        // lazy-compute on-the-fly notifies the current reactive again
        eager: true,
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
        const threadName = this.thread?.name?.trim().toLowerCase();
        const defaultSubject = this.default_subject ? this.default_subject.toLowerCase() : "";
        const candidates = new Set([defaultSubject, threadName]);
        return candidates.has(this.subject?.toLowerCase());
    }

    get resUrl() {
        return `${url("/web")}#model=${this.thread.model}&id=${this.thread.id}`;
    }

    get editDate() {
        return this.write_date !== this.create_date ? this.write_date : false;
    }

    get hasTextContent() {
        return /*(this.editDate && this.attachments.length) || */ !this.isBodyEmpty;
    }

    isEmpty = Record.attr(false, {
        /** @this {import("models").Message} */
        compute() {
            return (
                this.isBodyEmpty &&
                this.attachments.length === 0 &&
                this.trackingValues.length === 0 &&
                !this.subtype_description
            );
        },
        /** @this {import("models").Message} */
        onUpdate() {
            if (this.isEmpty && this.starred) {
                const starred = this.store.discuss.starred;
                starred.counter--;
                starred.messages.delete(this);
            }
        },
    });
    isBodyEmpty = Record.attr(undefined, {
        compute() {
            return (
                !this.body ||
                ["", "<p></p>", "<p><br></p>", "<p><br/></p>"].includes(
                    this.body.replace(/\s/g, "")
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

    get editDatetimeHuge() {
        return deserializeDateTime(this.editDate).toLocaleString(
            omit(DateTime.DATETIME_HUGE, "timeZoneName")
        );
    }

    get scheduledDateSimple() {
        return this.scheduledDatetime.toLocaleString(DateTime.TIME_24_SIMPLE, {
            locale: user.lang?.replace("_", "-"),
        });
    }

    async edit(body, attachments = [], { mentionedChannels = [], mentionedPartners = [] } = {}) {
        if (convertBrToLineBreak(this.body) === body && attachments.length === 0) {
            return;
        }
        const validMentions = this.store.getMentionsFromText(body, {
            mentionedChannels,
            mentionedPartners,
        });
        const messageData = await rpc("/mail/message/update_content", {
            attachment_ids: attachments.concat(this.attachments).map((attachment) => attachment.id),
            attachment_tokens: attachments
                .concat(this.attachments)
                .map((attachment) => attachment.accessToken),
            body: await prettifyMessageContent(body, validMentions),
            message_id: this.id,
            partner_ids: validMentions?.partners?.map((partner) => partner.id),
        });
        this.store.Message.insert(messageData, { html: true });
        if (this.hasLink && this.store.hasLinkPreviewFeature) {
            rpc("/mail/link_preview", { message_id: this.id }, { silent: true });
        }
    }

    async react(content) {
        await rpc(
            "/mail/message/reaction",
            {
                action: "add",
                content,
                message_id: this.id,
            },
            { silent: true }
        );
    }

    async remove() {
        await rpc("/mail/message/update_content", {
            attachment_ids: [],
            attachment_tokens: [],
            body: "",
            message_id: this.id,
        });
        this.body = "";
        this.attachments = [];
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
}

Message.register();
