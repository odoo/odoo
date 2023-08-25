/* @odoo-module */

import { Record } from "@mail/core/common/record";

import { _t } from "@web/core/l10n/translation";

let nextId = 1;
export class NotificationGroup extends Record {
    /** @type {import("@mail/core/common/notification_model").Notification[]} */
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
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    constructor(store) {
        super();
        this._store = store;
        this._store.NotificationGroup.records.push(this);
        this.id = nextId++;
        // return reactive
        return store.NotificationGroup.records.find((group) => group.eq(this));
    }

    get iconSrc() {
        return "/mail/static/src/img/smiley/mailfailure.jpg";
    }

    get body() {
        return _t("An error occurred when sending an email");
    }

    get lastMessage() {
        return this._store.Message.records[this.lastMessageId];
    }

    get datetime() {
        return this.lastMessage?.datetime;
    }
}
