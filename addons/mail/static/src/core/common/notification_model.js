import { Record } from "@mail/core/common/record";

import { _t } from "@web/core/l10n/translation";

export class Notification extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Notification>} */
    static records = {};
    /** @returns {import("models").Notification} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Notification|import("models").Notification[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {number} */
    id;
    message = Record.one("Message", {
        onDelete() {
            this.delete();
        },
    });
    /** @type {string} */
    notification_status;
    /** @type {string} */
    notification_type;
    failure = Record.one("Failure", {
        inverse: "notifications",
        /** @this {import("models").Notification} */
        compute() {
            const thread = this.message?.thread;
            if (!this.message?.isSelfAuthored) {
                return;
            }
            const failure = Object.values(this.store.Failure.records).find((f) => {
                return (
                    f.resModel === thread?.model &&
                    f.type === this.notification_type &&
                    (f.resModel !== "discuss.channel" || f.resIds.has(thread?.id))
                );
            });
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
    persona = Record.one("Persona");

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
                return "fa fa-exclamation";
            case "ready":
                return "fa fa-send-o";
            case "canceled":
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
                return _t("Ready");
            case "canceled":
                return _t("Cancelled");
        }
        return "";
    }
}

Notification.register();
