import { BusPlugin } from "@bus/services/bus_plugin";
import { OutOfFocusPlugin } from "@mail/core/common/out_of_focus_plugin";
import { StorePlugin } from "@mail/core/common/store_plugin";

import { Plugin, usePlugin } from "@odoo/owl";

import { GlobalBusPlugin } from "@web/core/global_bus_plugin";
import { services } from "@web/core/services";

export class MailCoreWebPlugin extends Plugin {
    /** Started with the store it uses (see `StorePlugin`). */
    static sequence = 110;

    #busService = usePlugin(BusPlugin);
    #bus = usePlugin(GlobalBusPlugin).bus;
    #outOfFocus = usePlugin(OutOfFocusPlugin);
    #store = usePlugin(StorePlugin);

    setup() {
        this.#busService.subscribe("mail.activity/updated", (payload, { id: notifId }) => {
            if (notifId <= this.#store.activity_counter_bus_id) {
                return;
            }
            let countDiff = 0;
            if ("count_diff" in payload) {
                countDiff = payload.count_diff;
            } else if (payload.activity_created) {
                countDiff = 1;
            } else if (payload.activity_deleted) {
                countDiff = -1;
            }
            this.#store.activityCounter = Math.max(this.#store.activityCounter + countDiff, 0);
        });
        this.#bus.addEventListener("mail.message/delete", ({ detail: { message } }) => {
            if (message.needaction) {
                this._dropFromNotificationCounter([message.id]);
            }
        });
        this.#busService.subscribe("mail.message/notification", (payload, { id: notifId }) => {
            const { message_id: messageId, store_data } = payload;
            this.#store.insert(store_data);
            /** @type {import("models").Message} */
            const message = this.#store["mail.message"].get(messageId);
            if (message.thread && notifId > message.thread.message_needaction_counter_bus_id) {
                message.thread.message_needaction_counter++;
            }
            if (this.#store.self_user?.im_status !== "busy") {
                this.#outOfFocus.notify(message);
            }
        });
        this.#busService.subscribe("mail.message/mark_as_unread", (payload, { id: notifId }) => {
            const { message_ids: messageIds, store_data } = payload;
            this.#store.insert(store_data);
            for (const messageId of messageIds) {
                const message = this.#store["mail.message"].get(messageId);
                if (message.thread && notifId > message.thread.message_needaction_counter_bus_id) {
                    message.thread.message_needaction_counter++;
                }
            }
        });
        this.#busService.subscribe("mail.message/mark_as_read", (payload, { id: notifId }) => {
            const { message_ids: messageIds } = payload;
            const unloadedMessageIds = [];
            for (const messageId of messageIds) {
                // We need to ignore all not yet known messages because we don't want them
                // to be shown partially as they would be linked directly to cache.
                // Furthermore, server should not send back all messageIds marked as read
                // but something like last read messageId or something like that.
                // (just imagine you mark 1000 messages as read ... )
                const message = this.#store["mail.message"].get(messageId);
                if (!message) {
                    unloadedMessageIds.push(messageId);
                    continue;
                }
                // update thread counter before needaction changes
                const thread = message.thread;
                if (
                    thread &&
                    message.needaction &&
                    notifId > thread.message_needaction_counter_bus_id &&
                    thread.message_needaction_counter > 0
                ) {
                    thread.message_needaction_counter--;
                }
                message.needaction = false;
                message.needaction_done = true;
            }
            if (unloadedMessageIds.length) {
                this._dropFromNotificationCounter(unloadedMessageIds);
            }
        });
        window.navigator.serviceWorker?.addEventListener(
            "message",
            ({ data: { action, data } }) => {
                if (action === "OPEN_RECORD") {
                    this.#store["mail.thread"].insert({ id: data.id, model: data.model }).open();
                }
            }
        );
    }

    /**
     * Drops the given messages from `init_counter_ids`, the ids the notification tab
     * counts as long as they are not loaded client-side.
     *
     * @param {number[]} messageIds
     */
    _dropFromNotificationCounter(messageIds) {
        const tab = this.#store.messagingMenu.notificationTab;
        // Notifications handled by email have no tab, hence no counter to update.
        if (!tab) {
            return;
        }
        const droppedIds = new Set(messageIds);
        tab.init_counter_ids = tab.init_counter_ids.filter((id) => !droppedIds.has(id));
    }
}

services.add(MailCoreWebPlugin);
