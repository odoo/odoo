/* @odoo-module */

import { Record } from "@mail/core/common/record";

import { _t } from "@web/core/l10n/translation";

export class Notification extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Models["Notification"]>} */
    static records = {};
    /** @returns {import("models").Models["Notification"]} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {import("models").Models["Notification"]} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {import("models").Models["Notification"]}
     */
    static insert(data) {
        const notification = this.get(data) ?? this.new(data);
        Object.assign(notification, { id: data.id });
        this.env.services["mail.message"].updateNotification(notification, data);
        return notification;
    }

    /** @type {number} */
    id;
    message = Record.one("Message");
    /** @type {string} */
    notification_status;
    /** @type {string} */
    notification_type;
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
            case "sent":
                return _t("Sent");
            case "bounce":
                return _t("Bounced");
            case "exception":
                return _t("Error");
            case "ready":
                return _t("Ready");
            case "canceled":
                return _t("Canceled");
        }
        return "";
    }
}

Notification.register();
