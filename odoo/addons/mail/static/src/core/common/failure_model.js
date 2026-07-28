/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { assignIn } from "@mail/utils/common/misc";
import { markRaw } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

export class Failure extends Record {
    static nextId = markRaw({ value: 1 });
    static id = "id";
    /** @type {Object.<number, import("models").Failure>} */
    static records = {};
    static new(data) {
        /** @type {import("models").Failure} */
        const failure = super.new(data);
        Record.onChange(failure, "notifications", () => {
            if (failure.notifications.length === 0) {
                failure.delete();
            }
        });
        return failure;
    }
    /** @returns {import("models").Failure} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Failure|import("models").Failure[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static _insert() {
        /** @type {import("models").Failure} */
        const failure = super._insert(...arguments);
        if (failure.notifications.length === 0) {
            failure.delete();
        } else {
            this.store.failures.add(failure);
        }
        return failure;
    }

    update(data) {
        assignIn(this, data, ["notifications"]);
        this.lastMessage = this.notifications[0]?.message;
        for (const notification of this.notifications) {
            if (this.lastMessage?.id < notification.message?.id) {
                this.lastMessage = notification.message;
            }
        }
        this.resIds.add(data.resId);
    }

    delete() {
        this._store.failures.delete(this);
        super.delete();
    }

    notifications = Record.many("Notification");
    get modelName() {
        return this.notifications?.[0]?.message?.originThread?.modelName;
    }
    get resModel() {
        return this.notifications?.[0]?.message?.originThread?.model;
    }
    lastMessage = Record.one("Message");
    /** @type {Set<number>} */
    resIds = new Set();
    /** @type {'sms' | 'email'} */
    get type() {
        return this.notifications?.[0]?.notification_type;
    }
    get status() {
        return this.notifications?.[0]?.notification_status;
    }

    get iconSrc() {
        return "/mail/static/src/img/smiley/mailfailure.svg";
    }

    get body() {
        return _t("An error occurred when sending an email");
    }

    get datetime() {
        return this.lastMessage?.datetime;
    }
}

Failure.register();
