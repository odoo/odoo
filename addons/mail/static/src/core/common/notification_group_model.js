/* @odoo-module */

import { Record, modelRegistry } from "@mail/core/common/record";
import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";

import { _t } from "@web/core/l10n/translation";

let nextId = 1;
export class NotificationGroup extends Record {
    static ids = ["id"];
    /** @type {NotificationGroup[]} */
    static records = [];

    static insert(data) {
        let group = this.records.find((group) => {
            return (
                group.resModel === data.resModel &&
                group.type === data.type &&
                (group.resModel !== "discuss.channel" || group.resIds.has(data.resId))
            );
        });
        if (!group) {
            group = new NotificationGroup(this.store);
        }
        this.update(group, data);
        if (group.notifications.length === 0) {
            removeFromArrayWithPredicate(this.records, (gr) => gr.eq(group));
        }
        return group;
    }

    static update(group, data) {
        Object.assign(group, {
            modelName: data.modelName ?? group.modelName,
            resModel: data.resModel ?? group.resModel,
            type: data.type ?? group.type,
            status: data.status ?? group.status,
        });
        const notifications = data.notifications ?? [];
        const alreadyKnownNotifications = new Set(group.notifications.map(({ id }) => id));
        const notificationIdsToRemove = new Set();
        for (const [commandName, notification] of notifications) {
            if (commandName === "insert" && !alreadyKnownNotifications.has(notification.id)) {
                group.notifications.push(notification);
            } else if (commandName === "insert-and-unlink") {
                notificationIdsToRemove.add(notification.id);
            }
        }
        group.notifications = group.notifications.filter(
            ({ id }) => !notificationIdsToRemove.has(id)
        );
        group.lastMessageId = group.notifications[0]?.message.id;
        for (const notification of group.notifications) {
            if (group.lastMessageId < notification.message.id) {
                group.lastMessageId = notification.message.id;
            }
        }
        group.resIds.add(data.resId);
    }

    /** @type {number} */
    id;
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
        super(store);
        this._store = store;
        this._store.NotificationGroup.records.push(this);
        this.id = nextId++;
        // return reactive
        return store.notificationGroups.find((group) => group.eq(this));
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

modelRegistry.add(NotificationGroup.name, NotificationGroup);
