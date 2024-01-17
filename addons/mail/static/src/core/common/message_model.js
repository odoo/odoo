/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { htmlToTextContentInline } from "@mail/utils/common/format";

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
    /** @type {string} */
    default_subject;
    /** @type {number|string} */
    id;
    /** @type {boolean} */
    is_discussion;
    /** @type {boolean} */
    is_note;
    /** @type {boolean} */
    is_transient;
    linkPreviews = Record.many("LinkPreview", { inverse: "message" });
    /** @type {number[]} */
    needaction_partner_ids = [];
    /** @type {number[]} */
    history_partner_ids = [];
    parentMessage = Record.one("Message");
    reactions = Record.many("MessageReactions", { inverse: "message" });
    notifications = Record.many("Notification", { inverse: "message" });
    recipients = Record.many("Persona");
    originThread = Record.one("Thread");
    /** @type {string} */
    scheduledDatetime;
    starredPersonas = Record.many("Persona");
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

    get editable() {
        if (!this._store.self.isAdmin && !this.isSelfAuthored) {
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
        return this._store.self.in(this.recipients);
    }

    get isHighlightedFromMention() {
        return this.isSelfMentioned && this.originThread?.model === "discuss.channel";
    }

    get isSelfAuthored() {
        if (!this.author) {
            return false;
        }
        return this.author.eq(this._store.self);
    }

    get isStarred() {
        return this._store.self.in(this.starredPersonas);
    }

    get isNeedaction() {
        return (
            this._store.self.type === "partner" &&
            this.needaction_partner_ids.includes(this._store.self.id)
        );
    }

    get hasActions() {
        return !this.is_transient;
    }

    get isHistory() {
        return (
            this._store.self.type === "partner" &&
            this.history_partner_ids.includes(this._store.self.id)
        );
    }

    get isNotification() {
        return (
            this.message_type === "notification" && this.originThread?.model === "discuss.channel"
        );
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
        const defaultSubject = this.default_subject ? this.default_subject.toLowerCase() : "";
        const candidates = new Set([defaultSubject, threadName]);
        return candidates.has(this.subject?.toLowerCase());
    }

    get resUrl() {
        return `${url("/web")}#model=${this.originThread?.model}&id=${this.originThread?.id}`;
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
            if (this.isEmpty && this.isStarred) {
                this.starredPersonas.delete(this._store.self);
                const starred = this._store.discuss.starred;
                starred.counter--;
                starred.messages.delete(this);
            }
        },
    });
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
