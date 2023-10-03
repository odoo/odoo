/* @odoo-module */

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
    /**
     * @param {Object} data
     * @returns {import("models").Notification}
     */
    static insert(data) {
        /** @type {import("models").Notification} */
        const notification = this.preinsert(data);
        notification.update(data);
        return notification;
    }

    update(data) {
        Object.assign(this, {
            message: data.message,
            notification_status: data.notification_status,
            notification_type: data.notification_type,
            failure_type: data.failure_type,
            persona: data.res_partner_id
                ? {
                      id: data.res_partner_id[0],
                      displayName: data.res_partner_id[1],
                      type: "partner",
                  }
                : undefined,
        });
        if (!this.message.author?.eq(this._store.self)) {
            return;
        }
        const thread = this.message.originThread;
        this._store.NotificationGroup.insert({
            modelName: thread?.modelName,
            resId: thread?.id,
            resModel: thread?.model,
            status: this.notification_status,
            type: this.notification_type,
            notifications: [[this.isFailure ? "ADD" : "DELETE", this]],
        });
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
