/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";

import { _t } from "@web/core/l10n/translation";

export class Notification extends DiscussModel {
    static id = ["id"];

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

    constructor(store, data) {
        super(store, data);
        Object.assign(this, {
            id: data.id,
            _store: store,
        });
    }

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

export class NotificationManager extends DiscussModelManager {
    /** @type {typeof Notification} */
    class;
    /** @type {Object.<number, Notification>} */
    records = {};

    /**
     * @param {Object} data
     * @returns {Notification}
     */
    insert(data) {
        let notification = this.records[data.id];
        if (!notification) {
            this.records[data.id] = new Notification(this.store, data);
            notification = this.records[data.id];
            notification.objectId = this._createObjectId(data);
        }
        this.update(notification, data);
        return notification;
    }

    update(notification, data) {
        Object.assign(notification, {
            messageId: data.messageId,
            notification_status: data.notification_status,
            notification_type: data.notification_type,
            failure_type: data.failure_type,
            persona: data.res_partner_id
                ? this.store.Persona.insert({
                      id: data.res_partner_id[0],
                      displayName: data.res_partner_id[1],
                      type: "partner",
                  })
                : undefined,
        });
        if (notification.message.author !== this.store.self) {
            return;
        }
        const thread = notification.message.originThread;
        this.store.NotificationGroup.insert({
            modelName: thread?.modelName,
            resId: thread?.id,
            resModel: thread?.model,
            status: notification.notification_status,
            type: notification.notification_type,
            notifications: [
                [notification.isFailure ? "insert" : "insert-and-unlink", notification],
            ],
        });
    }
}

discussModelRegistry.add("Notification", [Notification, NotificationManager]);
