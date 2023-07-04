/* @odoo-module */

import { htmlToTextContentInline } from "@mail/utils/format";

import { toRaw } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { url } from "@web/core/utils/urls";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { createLocalId } from "../utils/misc";
import { omit } from "@web/core/utils/objects";

const { DateTime } = luxon;

export class Message {
    /** @type {Object[]} */
    attachments = [];
    /** @type {import("@mail/core/persona_model").Persona} */
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
    /** @type {import("@mail/core/notification_model").Notification[]} */
    notifications = [];
    /** @type {import("@mail/core/persona_model").Persona[]} */
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
    pinned_at;
    /** @type {string} */
    create_date;
    /** @type {string} */
    write_date;

    /**
     * We exclude the milliseconds because datetime string from the server don't
     * have them. Message without date like transient message can be missordered
     */
    now = DateTime.now().set({ milliseconds: 0 });
    /** @type {import("@mail/core/store_service").Store} */
    _store;

    /**
     * @returns {boolean}
     */
    get editable() {
        if (!this._store.user?.isAdmin && !this.isSelfAuthored) {
            return false;
        }
        if (this.type !== "comment") {
            return false;
        }
        return this.isNote || this.resModel === "discuss.channel";
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
        return this.recipients.some((recipient) => recipient === this._store.self);
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
        return this._store.threads[createLocalId(this.resModel, this.resId)];
    }

    get resUrl() {
        return `${url("/web")}#model=${this.resModel}&id=${this.resId}`;
    }

    get editDate() {
        return this.write_date !== this.create_date ? this.write_date : false;
    }

    get hasTextContent() {
        return (this.editDate && this.attachments.length) || !this.isBodyEmpty;
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

    get pinnedAt() {
        if (!this.pinned_at) {
            return null;
        }
        return luxon.DateTime.fromISO(new Date(this.pinned_at).toISOString());
    }

    get editDatetimeHuge() {
        return deserializeDateTime(this.editDate).toLocaleString(
            omit(DateTime.DATETIME_HUGE, "timeZoneName")
        );
    }
}
