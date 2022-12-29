/* @odoo-module */

import { htmlToTextContentInline } from "@mail/new/utils/format";

import { toRaw } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { url } from "@web/core/utils/urls";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { createLocalId } from "../utils/misc";

const { DateTime } = luxon;

export class Message {
    /** @type {Object[]} */
    attachments = [];
    /** @type {import("@mail/new/core/persona_model").Persona} */
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
    /** @type {Notification[]} */
    notifications = [];
    /** @type {import("@mail/new/core/persona_model").Persona[]} */
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
    /**
     * We exclude the milliseconds because datetime string from the server don't
     * have them. Message without date like transient message can be missordered
     */
    now = DateTime.now().set({ milliseconds: 0 });
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;

    /**
     * @returns {string}
     */
    get authorAvatarUrl() {
        if (this.author && (!this.originThread || this.originThread.model !== "mail.channel")) {
            // TODO FIXME for public user this might not be accessible. task-2223236
            // we should probably use the correspondig attachment id + access token
            // or create a dedicated route to get message image, checking the access right of the message
            return this.author.avatarUrl;
        } else if (
            this.author?.type === "partner" &&
            this.originThread &&
            this.originThread.model === "mail.channel"
        ) {
            return `/mail/channel/${this.originThread.id}/partner/${this.author.id}/avatar_128`;
        } else if (
            this.author?.type === "guest" &&
            this.originThread &&
            this.originThread.model === "mail.channel"
        ) {
            return `/mail/channel/${this.originThread.id}/guest/${this.author.id}/avatar_128?unique=${this.author.name}`;
        } else if (this.type === "email") {
            return "/mail/static/src/img/email_icon.png";
        }
        return "/mail/static/src/img/smiley/avatar.jpg";
    }

    /**
     * @returns {boolean}
     */
    get editable() {
        if (this.isEmpty) {
            return false;
        }
        if (!this._store.user?.isAdmin && !this.isSelfAuthored) {
            return false;
        }
        if (this.type !== "comment") {
            return false;
        }
        return this.isNote || this.resModel === "mail.channel";
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

    get scheduledDateShort() {
        return this.scheduledDate.toLocaleString(DateTime.TIME_SIMPLE);
    }

    get datetimeSimpleStr() {
        return this.datetime.toLocaleString(DateTime.TIME_SIMPLE);
    }

    get datetimeShort() {
        return this.datetime.toLocaleString(DateTime.DATETIME_SHORT);
    }

    get isSelfMentioned() {
        return this.recipients.some((recipient) => recipient === this._store.self);
    }

    get isHighlightedFromMention() {
        return this.isSelfMentioned && this.resModel === "mail.channel";
    }

    get isSelfAuthored() {
        if (!this.author) {
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
        return this.type === "notification" && this.resModel === "mail.channel";
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

    get url() {
        return `${url("/web")}#model=${this.resModel}&id=${this.id}`;
    }

    get isBodyEmpty() {
        return (
            !this.body ||
            ["", "<p></p>", "<p><br></p>", "<p><br/></p>"].includes(this.body.replace(/\s/g, ""))
        );
    }

    get isEmpty() {
        return (
            this.isBodyEmpty &&
            this.attachments.length === 0 &&
            this.trackingValues.length === 0 &&
            !this.subtypeDescription
        );
    }

    get inlineBody() {
        if (!this.body) {
            return "";
        }
        return htmlToTextContentInline(this.body);
    }

    get failureNotifications() {
        return this.notifications.filter((notification) => notification.isFailure);
    }
}
