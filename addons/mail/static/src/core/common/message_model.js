/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";
import { replaceArrayWithCompare } from "@mail/utils/common/arrays";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { assignDefined } from "@mail/utils/common/misc";

import { toRaw } from "@odoo/owl";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { omit } from "@web/core/utils/objects";
import { url } from "@web/core/utils/urls";

const { DateTime } = luxon;

export class Message extends DiscussModel {
    static id = ["id"];

    /** @type {Object[]} */
    attachments = [];
    /** @type {import("@mail/core/common/persona_model").Persona} */
    author;
    /** @type {string} */
    body;
    /** @type {string} */
    defaultSubject;
    /** @type {number|string} */
    id;
    /** @type {boolean} */
    isDiscussion;
    /** @type {boolean} */
    isNote;
    /** @type {boolean} */
    isStarred;
    /** @type {boolean} */
    isTransient;
    /** @type {LinkPreview[]} */
    linkPreviews = [];
    /** @type {number[]} */
    needaction_partner_ids = [];
    /** @type {number[]} */
    history_partner_ids = [];
    /** @type {Message|undefined} */
    parentMessage;
    /** @type {MessageReactions[]} */
    reactions = [];
    /** @type {import("@mail/core/common/notification_model").Notification[]} */
    notifications = [];
    /** @type {import("@mail/core/common/persona_model").Persona[]} */
    recipients = [];
    /** @type {number|string} */
    resId;
    /** @type {string|undefined} */
    resModel;
    /** @type {string} */
    scheduledDatetime;
    /** @type {Number[]} */
    starred_partner_ids = [];
    /** @type {string} */
    subject;
    /** @type {string} */
    subtypeDescription;
    /** @type {Object[]} */
    trackingValues = [];
    /** @type {string} */
    type;
    /** @type {string} */
    temporary_id = null;
    /** @type {string|undefined} */
    notificationType;
    /** @type {string} */
    create_date;
    /** @type {string} */
    write_date;

    /**
     * We exclude the milliseconds because datetime string from the server don't
     * have them. Message without date like transient message can be missordered
     */
    now = DateTime.now().set({ milliseconds: 0 });
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    /**
     * @returns {boolean}
     */
    get editable() {
        if (!this._store.user?.isAdmin && !this.isSelfAuthored) {
            return false;
        }
        return this.type === "comment";
    }

    get dateDay() {
        let dateDay = this.datetime.toLocaleString(DateTime.DATE_FULL);
        if (dateDay === DateTime.now().toLocaleString(DateTime.DATE_FULL)) {
            dateDay = _t("Today");
        }
        return dateDay;
    }

    get datetime() {
        if (!this._datetime) {
            this._datetime = toRaw(this.date ? deserializeDateTime(this.date) : this.now);
        }
        return this._datetime;
    }

    get scheduledDate() {
        return toRaw(
            this.scheduledDatetime ? deserializeDateTime(this.scheduledDatetime) : undefined
        );
    }

    get datetimeShort() {
        return this.datetime.toLocaleString(DateTime.DATETIME_SHORT);
    }

    get isSelfMentioned() {
        return this.recipients.some((recipient) => recipient.equals(this._store.self));
    }

    get isHighlightedFromMention() {
        return this.isSelfMentioned && this.resModel === "discuss.channel";
    }

    get isSelfAuthored() {
        if (!this.author || !this._store.self) {
            return false;
        }
        return this.author.id === this._store.self.id && this.author.type === this._store.self.type;
    }

    get isNeedaction() {
        return this.needaction_partner_ids.includes(this._store.user?.id);
    }

    get hasActions() {
        return !this.isTransient;
    }

    /**
     * @returns {boolean}
     */
    get isHistory() {
        return this.history_partner_ids.includes(this._store.user?.id);
    }

    /**
     * @returns {boolean}
     */
    get isNotification() {
        return this.type === "notification" && this.resModel === "discuss.channel";
    }

    get isSubjectSimilarToOriginThreadName() {
        if (!this.subject || !this.originThread || !this.originThread.name) {
            return false;
        }
        const regexPrefix = /^((re|fw|fwd)\s*:\s*)*/i;
        const cleanedThreadName = this.originThread.name.replace(regexPrefix, "");
        const cleanedSubject = this.subject.replace(regexPrefix, "");
        return cleanedSubject === cleanedThreadName;
    }

    get isSubjectDefault() {
        const threadName = this.originThread?.name?.trim().toLowerCase();
        const defaultSubject = this.defaultSubject ? this.defaultSubject.toLowerCase() : "";
        const candidates = new Set([defaultSubject, threadName]);
        return candidates.has(this.subject?.toLowerCase());
    }

    get originThread() {
        return this._store.Thread.findById({ model: this.resModel, id: this.resId });
    }

    get resUrl() {
        return `${url("/web")}#model=${this.resModel}&id=${this.resId}`;
    }

    get editDate() {
        return this.write_date !== this.create_date ? this.write_date : false;
    }

    get hasTextContent() {
        return /*(this.editDate && this.attachments.length) || */ !this.isBodyEmpty;
    }

    get isEmpty() {
        return (
            this.isBodyEmpty &&
            this.attachments.length === 0 &&
            this.trackingValues.length === 0 &&
            !this.subtypeDescription
        );
    }
    get isBodyEmpty() {
        return (
            !this.body ||
            ["", "<p></p>", "<p><br></p>", "<p><br/></p>"].includes(this.body.replace(/\s/g, ""))
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
            this._store.hasLinkPreviewFeature &&
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
}

export class MessageManager extends DiscussModelManager {
    /** @type {typeof Message} */
    class;
    /** @type {Object.<number, Message>} */
    records = {};

    /**
     * @param {Object} data
     * @returns {Message}
     */
    insert(data) {
        let message;
        if (data.res_id) {
            this.store.Thread.insert({
                model: data.model,
                id: data.res_id,
            });
        }
        if (data.id in this.records) {
            message = this.records[data.id];
        } else {
            message = new Message();
            message._store = this.store;
            this.records[data.id] = message;
            message = this.records[data.id];
            message.objectId = this._createObjectId(data);
        }
        this.update(message, data);
        // return reactive version
        return message;
    }

    /**
     * @param {import("@mail/core/common/message_model").Message} message
     * @param {Object} data
     */
    update(message, data) {
        const {
            attachment_ids: attachments = message.attachments,
            default_subject: defaultSubject = message.defaultSubject,
            is_discussion: isDiscussion = message.isDiscussion,
            is_note: isNote = message.isNote,
            is_transient: isTransient = message.isTransient,
            linkPreviews = message.linkPreviews,
            message_type: type = message.type,
            model: resModel = message.resModel,
            module_icon,
            notifications = message.notifications,
            parentMessage,
            recipients = message.recipients,
            record_name,
            res_id: resId = message.resId,
            res_model_name,
            subtype_description: subtypeDescription = message.subtypeDescription,
            ...remainingData
        } = data;
        assignDefined(message, remainingData);
        assignDefined(message, {
            defaultSubject,
            isDiscussion,
            isNote,
            isStarred: this.store.user
                ? message.starred_partner_ids.includes(this.store.user.id)
                : false,
            isTransient,
            parentMessage: parentMessage ? this.insert(parentMessage) : undefined,
            resId,
            resModel,
            subtypeDescription,
            type,
        });
        // origin thread before other information (in particular notification insert uses it)
        if (message.originThread) {
            assignDefined(message.originThread, {
                modelName: res_model_name || undefined,
                module_icon: module_icon || undefined,
                name: record_name || undefined,
            });
        }
        replaceArrayWithCompare(
            message.attachments,
            attachments.map((attachment) =>
                this.store.Attachment.insert({ message, ...attachment })
            )
        );
        if (
            Array.isArray(message.author) &&
            message.author.some((command) => command.includes("clear"))
        ) {
            message.author = undefined;
        }
        if (data.author?.id) {
            message.author = this.store.Persona.insert({
                ...data.author,
                type: "partner",
            });
        }
        if (data.guestAuthor?.id) {
            message.author = this.store.Persona.insert({
                ...data.guestAuthor,
                type: "guest",
                channelId: message.originThread.id,
            });
        }
        replaceArrayWithCompare(
            message.linkPreviews,
            linkPreviews.map((data) => this.store.LinkPreview.insert({ ...data, message }))
        );
        replaceArrayWithCompare(
            message.notifications,
            notifications.map((notification) =>
                this.store.Notification.insert({ ...notification, messageId: message.id })
            )
        );
        replaceArrayWithCompare(
            message.recipients,
            recipients.map((recipient) =>
                this.store.Persona.insert({ ...recipient, type: "partner" })
            )
        );
        if ("user_follower_id" in data && data.user_follower_id && this.store.self) {
            message.originThread.selfFollower = this.store.Follower.insert({
                followedThread: message.originThread,
                id: data.user_follower_id,
                isActive: true,
                partner: this.store.self,
            });
        }
        if (data.messageReactionGroups) {
            this._updateReactions(message, data.messageReactionGroups);
        }
        if (message.isNotification && !message.notificationType) {
            const parser = new DOMParser();
            const htmlBody = parser.parseFromString(message.body, "text/html");
            message.notificationType =
                htmlBody.querySelector(".o_mail_notification")?.dataset.oeType;
        }
        this.env.bus.trigger("mail.message/onUpdate", { message, data });
    }

    _updateReactions(message, reactionGroups) {
        const reactionContentToUnlink = new Set();
        const reactionsToInsert = [];
        for (const rawReaction of reactionGroups) {
            const [command, reactionData] = Array.isArray(rawReaction)
                ? rawReaction
                : ["insert", rawReaction];
            const reaction = this.store.MessageReactions.insert(reactionData);
            if (command === "insert") {
                reactionsToInsert.push(reaction);
            } else {
                reactionContentToUnlink.add(reaction.content);
            }
        }
        message.reactions = message.reactions.filter(
            ({ content }) => !reactionContentToUnlink.has(content)
        );
        for (const reaction of reactionsToInsert) {
            const idx = message.reactions.findIndex(({ content }) => reaction.content === content);
            if (idx !== -1) {
                message.reactions[idx] = reaction;
            } else {
                message.reactions.push(reaction);
            }
        }
    }

    /**
     * @returns {number}
     */
    getLastMessageId() {
        return Object.values(this.records).reduce(
            (lastMessageId, message) => Math.max(lastMessageId, message.id),
            0
        );
    }

    getNextTemporaryId() {
        return this.getLastMessageId() + 0.01;
    }
}

discussModelRegistry.add("Message", [Message, MessageManager]);
