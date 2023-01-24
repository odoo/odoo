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
    now = DateTime.now();
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;

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
        return toRaw(this.date ? deserializeDateTime(this.date) : this.now);
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
        return this.author.id === this._store.self.id;
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
        const cleanedThreadName = this.originThread.name.trim().toLowerCase();
        const cleanedSubject = this.subject.trim().toLowerCase();
        if (cleanedSubject === cleanedThreadName) {
            return true;
        }
        if (!cleanedSubject.endsWith(cleanedThreadName)) {
            return false;
        }
        const subjectWithoutThreadName = cleanedSubject.slice(
            0,
            cleanedSubject.indexOf(cleanedThreadName)
        );
        const prefixList = ["re", "fw", "fwd"];
        // match any prefix as many times as possible
        const isSequenceOfPrefixes = new RegExp(`^((${prefixList.join("|")}):\\s*)+$`);
        return isSequenceOfPrefixes.test(subjectWithoutThreadName);
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
        return htmlToTextContentInline(this.body);
    }

    get failureNotifications() {
        return this.notifications.filter((notification) => notification.isFailure);
    }
}
