/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Record } from "@mail/core/record";

let nextId = 1;
export class NotificationGroup extends Record {
    /** @type {import("@mail/core/notification_model").Notification[]} */
    notifications = [];
    /** @type {string} */
    modelName;
    /** @type {string} */
    resModel;
    /** @type {number} */
    lastMessageId;
    /** @type {Set<number>} */
    resIds = new Set();
    /** @type {'sms' | 'email'} */
    type;
    /** @type {import("@mail/core/store_service").Store} */
    _store;

    constructor(store) {
        super();
        this._store = store;
        this._store.notificationGroups.push(this);
        this.id = nextId++;
        // return reactive
        return store.notificationGroups.find((group) => group === this);
    }

    get iconSrc() {
        return "/mail/static/src/img/smiley/mailfailure.jpg";
    }

    get body() {
        return _t("An error occurred when sending an email");
    }

    get lastMessage() {
        return this._store.messages[this.lastMessageId];
    }

    get datetime() {
        return this.lastMessage?.datetime;
    }
}
