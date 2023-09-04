/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";

import { _t } from "@web/core/l10n/translation";

let nextId = 1;
export class NotificationGroup extends Record {
    static id = "id";
    /** @type {NotificationGroup[]} */
    static records = [];
    /**
     * @param {Object} data
     * @returns {NotificationGroup}
     */
    static insert(data) {
        let group = this.records.find((group) => {
            return (
                group.resModel === data.resModel &&
                group.type === data.type &&
                (group.resModel !== "discuss.channel" || group.resIds.has(data.resId))
            );
        });
        if (!group) {
            const id = nextId++;
            group = this.new({ id });
            Object.assign(group, { id, _store: this.store });
            this.store.NotificationGroup.records.push(group);
            // return reactive
            group = this.store.NotificationGroup.records.find((g) => g.eq(group));
        }
        this.env.services["mail.message"].updateNotificationGroup(group, data);
        if (group.notifications.length === 0) {
            removeFromArrayWithPredicate(this.records, (gr) => gr.eq(group));
        }
        return group;
    }

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

    get iconSrc() {
        return "/mail/static/src/img/smiley/mailfailure.jpg";
    }

    get body() {
        return _t("An error occurred when sending an email");
    }

    get lastMessage() {
        return this._store.Message.get(this.lastMessageId);
    }

    get datetime() {
        return this.lastMessage?.datetime;
    }
}

NotificationGroup.register();
