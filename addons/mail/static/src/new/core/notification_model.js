/* @odoo-module */

import { _t } from "@web/core/l10n/translation";

export class Notification {
    /** @type {number} */
    id;
    /** @type {number} */
    messageId;
    /** @type {string} */
    notification_status;
    /** @type {string} */
    notification_type;
    /** @type {import("@mail/new/core/persona_model").Persona} */
    partner;
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;

    constructor(store, data) {
        Object.assign(this, {
            id: data.id,
            _store: store,
        });
        store.notifications[this.id] = this;
    }

    get message() {
        return this._store.messages[this.messageId];
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
