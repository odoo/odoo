/* @odoo-module */

import { Record } from "@mail/core/common/record";

import { _t } from "@web/core/l10n/translation";

export class Notification extends Record {
    /** @type {Object.<number, Notification>} */
    static records = {};
    /**
     * @param {Object} data
     * @returns {Notification}
     */
    static insert(data) {
        let notification = this.records[data.id];
        if (!notification) {
            notification = new Notification();
            this.records[data.id] = notification;
            Object.assign(notification, {
                id: data.id,
                _store: this.store,
            });
            notification = this.records[data.id];
        }
        this.env.services["mail.message"].updateNotification(notification, data);
        return notification;
    }

    /** @type {number} */
    id;
    /** @type {number} */
    messageId;
    /** @type {string} */
    notification_status;
    /** @type {string} */
    notification_type;
    /** @type {string} */
    failure_type;
    /** @type {import("@mail/core/common/persona_model").Persona} */
    persona;
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    get message() {
        return this._store.Message.records[this.messageId];
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
