/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { assignDefined } from "@mail/utils/common/misc";

import { toRaw } from "@odoo/owl";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
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
    /**
     * @param {Object} data
     * @returns {import("models").Message}
     */
    static insert(data) {
        if (data.res_id) {
            this.store.Thread.insert({
                model: data.model,
                id: data.res_id,
            });
        }
        /** @type {import("models").Message} */
        const message = this.preinsert(data);
        message.update(data);
        return message;
    }

    /** @param {Object} data */
    update(data) {
        const {
            attachment_ids: attachments = this.attachments,
            default_subject: defaultSubject = this.defaultSubject,
            is_discussion: isDiscussion = this.isDiscussion,
            is_note: isNote = this.isNote,
            is_transient: isTransient = this.isTransient,
            linkPreviews = this.linkPreviews,
            message_type: type = this.type,
            model: resModel = this.resModel,
            module_icon,
            notifications = this.notifications,
            parentMessage,
            recipients = this.recipients,
            record_name,
            res_id: resId = this.resId,
            res_model_name,
            subtype_description: subtypeDescription = this.subtypeDescription,
            ...remainingData
        } = data;
        assignDefined(this, remainingData);
        assignDefined(this, {
            defaultSubject,
            isDiscussion,
            isNote,
            isStarred: this._store.user
                ? this.starred_partner_ids.includes(this._store.user.id)
                : false,
            isTransient,
            parentMessage: parentMessage || undefined,
            resId,
            resModel,
            subtypeDescription,
            type,
        });
        // origin thread before other information (in particular notification insert uses it)
        if (this.originThread) {
            assignDefined(this.originThread, {
                modelName: res_model_name || undefined,
                module_icon: module_icon || undefined,
                name:
                    this.originThread.model === "discuss.channel"
                        ? undefined
                        : record_name || undefined,
            });
        }
        this.attachments = attachments.map((attachment) => ({ message: this, ...attachment }));
        if ("author" in data) {
            this.author = data.author;
        }
        this.linkPreviews = linkPreviews.map((data) => ({ ...data, message: this }));
        this.notifications = notifications.map((notif) => ({ ...notif, message: this }));
        this.recipients = recipients.map((recipient) => ({ ...recipient, type: "partner" }));
        if ("user_follower_id" in data && data.user_follower_id && this._store.self) {
            this.originThread.selfFollower = {
                followedThread: this.originThread,
                id: data.user_follower_id,
                is_active: true,
                partner: this._store.self,
            };
        }
        if ("messageReactionGroups" in data) {
            this.reactions = data.messageReactionGroups;
        }
        if (this.isNotification && !this.notificationType) {
            const parser = new DOMParser();
            const htmlBody = parser.parseFromString(this.body, "text/html");
            this.notificationType = htmlBody.querySelector(".o_mail_notification")?.dataset.oeType;
        }
    }

    attachments = Record.many("Attachment");
    author = Record.one("Persona");
    /** @type {string} */
    body;
    composer = Record.one("Composer", { onDelete: (r) => r.delete() });
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
    linkPreviews = Record.many("LinkPreview");
    /** @type {number[]} */
    needaction_partner_ids = [];
    /** @type {number[]} */
    history_partner_ids = [];
    parentMessage = Record.one("Message");
    reactions = Record.many("MessageReactions");
    notifications = Record.many("Notification");
    recipients = Record.many("Persona");
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
        return this.datetime.toLocaleString(DateTime.DATETIME_SHORT_WITH_SECONDS);
    }

    get isSelfMentioned() {
        return this._store.self?.in(this.recipients);
    }

    get isSelfImportant() {
        return (
            this.resModel === "discuss.channel" &&
            (this.isSelfMentioned || this.parentMessage?.author?.eq(this._store.self))
        );
    }

    get isSelfAuthored() {
        if (!this.author || !this._store.self) {
            return false;
        }
        return this.author.eq(this._store.self);
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
        return this._store.Thread.get({ model: this.resModel, id: this.resId });
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

Message.register();
