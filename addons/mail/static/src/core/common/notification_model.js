import { fields, Record } from "@mail/core/common/record";

import { _t } from "@web/core/l10n/translation";

export class Notification extends Record {
    static _name = "mail.notification";
    static id = "id";

    /** @type {number} */
    id;
    mail_message_id = fields.One("mail.message", {
        onDelete() {
            this.delete();
        },
    });
    /** @type {string} */
    notification_status;
    /** @type {string} */
    notification_type;
    mail_email_address;
    failure = fields.One("Failure", {
        inverse: "notifications",
        /** @this {import("models").Notification} */
        compute() {
            const thread = this.mail_message_id?.thread;
            if (!this.mail_message_id?.isSelfAuthored) {
                return;
            }
            const failure = Object.values(this.store.Failure.records).find(
                (f) =>
                    f.resModel === thread?.model &&
                    f.type === this.notification_type &&
                    (f.resModel !== "discuss.channel" || f.resIds.has(thread?.id))
            );
            return this.isFailure
                ? {
                      id: failure ? failure.id : this.store.Failure.nextId.value++,
                  }
                : false;
        },
        eager: true,
    });
    /** @type {string} */
    failure_type;
    get failureMessage() {
        switch (this.failure_type) {
            case "mail_smtp":
                return _t("Connection failed");
            case "mail_bounce":
                return _t("Bounce");
            case "mail_email_invalid":
                return _t("Invalid email address");
            case "mail_email_missing":
                return _t("Missing email address");
            case "mail_from_invalid":
                return _t("Invalid from address");
            case "mail_from_missing":
                return _t("Missing from address");
            case "mail_spam":
                return _t("Detected As Spam");
            default:
                return _t("Exception");
        }
    }
    res_partner_id = fields.One("res.partner");

    /**
     * Get the translate string of the failure type only
     * when it corresponds to a failure type
     * that is automatically cancelled before sending.
     *
     * @returns {string}
     */
    get autoCanceledFailureType() {
        switch (this.failure_type) {
            case "mail_bl":
                return _t("Blacklisted Address");
            case "mail_dup":
                return _t("Duplicated Email");
            case "mail_optout":
                return _t("Opted Out");
        }
        return "";
    }

    get isFailure() {
        return ["exception", "bounce"].includes(this.notification_status);
    }

    get icon() {
        if (this.isFailure) {
            return "fa fa-envelope";
        }
        return "fa fa-envelope-o";
    }

    get label() {
        return "";
    }

    get isFollowerNotification() {
        return this.mail_message_id.thread.followers.some(
            (follower) => follower.partner_id.id === this.res_partner_id.id
        );
    }

    get statusIcon() {
        switch (this.notification_status) {
            case "process":
                return "fa fa-hourglass-half";
            case "pending":
                return "fa fa-paper-plane-o";
            case "sent":
                return "fa fa-check";
            case "bounce":
                return "fa fa-exclamation";
            case "exception":
                return "fa fa-times text-danger";
            case "ready":
                return "fa fa-send-o";
            case "canceled":
                if (this.autoCanceledFailureType) {
                    return "fa fa-remove";
                }
                return "fa fa-trash-o";
        }
        return "";
    }

    get statusTitle() {
        switch (this.notification_status) {
            case "process":
                return _t("Processing");
            case "pending":
                return _t("Sent");
            case "sent":
                return _t("Delivered");
            case "bounce":
                return _t("Bounced");
            case "exception":
                return _t("Error");
            case "ready":
                return _t("Queued");
            case "canceled":
                return this.autoCanceledFailureType || _t("Cancelled");
        }
        return "";
    }
}

Notification.register();
