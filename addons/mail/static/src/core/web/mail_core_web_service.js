import { proxy } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class MailCoreWeb {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.store = services["mail.store"];
    }

    setup() {
        this.busService.subscribe("mail.activity/updated", (payload, { id: notifId }) => {
            if (notifId <= this.store.activity_counter_bus_id) {
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
            this.store.activityCounter += countDiff;
        });
        this.env.bus.addEventListener("mail.message/delete", ({ detail: { message } }) => {
            if (this.store.messagingMenu.notificationTab && message.needaction) {
                this.store.messagingMenu.notificationTab.init_counter_ids =
                    this.store.messagingMenu.notificationTab.init_counter_ids.filter(
                        (id) => id !== message.id
                    );
            }
        });
        this.busService.subscribe("mail.message/inbox", (payload, { id: notifId }) => {
            const { message_id: messageId, store_data } = payload;
            this.store.insert(store_data);
            /** @type {import("models").Message} */
            const message = this.store["mail.message"].get(messageId);
            if (message.thread && notifId > message.thread.message_needaction_counter_bus_id) {
                message.thread.message_needaction_counter++;
            }
            if (this.store.self_user?.im_status !== "busy") {
                this.store.env.services["mail.out_of_focus"].notify(message);
            }
        });
        this.busService.subscribe("mail.message/mark_as_unread", (payload, { id: notifId }) => {
            const { message_ids: messageIds, store_data } = payload;
            this.store.insert(store_data);
            for (const messageId of messageIds) {
                const message = this.store["mail.message"].get(messageId);
                if (message.thread && notifId > message.thread.message_needaction_counter_bus_id) {
                    message.thread.message_needaction_counter++;
                }
            }
        });
        this.busService.subscribe("mail.message/mark_as_read", (payload, { id: notifId }) => {
            const { message_ids: messageIds } = payload;
            const unloadedMessageIds = [];
            for (const messageId of messageIds) {
                // We need to ignore all not yet known messages because we don't want them
                // to be shown partially as they would be linked directly to cache.
                // Furthermore, server should not send back all messageIds marked as read
                // but something like last read messageId or something like that.
                // (just imagine you mark 1000 messages as read ... )
                const message = this.store["mail.message"].get(messageId);
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
                const unloadedSet = new Set(unloadedMessageIds);
                this.store.messagingMenu.notificationTab.init_counter_ids =
                    this.store.messagingMenu.notificationTab.init_counter_ids.filter(
                        (id) => !unloadedSet.has(id)
                    );
            }
        });
    }
}

export const mailCoreWeb = {
    dependencies: ["bus_service", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        const mailCoreWeb = proxy(new MailCoreWeb(env, services));
        mailCoreWeb.setup();
        return mailCoreWeb;
    },
};

registry.category("services").add("mail.core.web", mailCoreWeb);
