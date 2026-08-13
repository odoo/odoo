import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class MailCoreWeb {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
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
        this.env.bus.addEventListener("mail.message/delete", ({ detail: { message, notifId } }) => {
            if (message.needaction && notifId > this.store.inbox.counter_bus_id) {
                this.store.inbox.counter--;
            }
            if (message.starred && notifId > this.store.starred.counter_bus_id) {
                this.store.starred.counter--;
            }
        });
        this.busService.subscribe("mail.message/inbox", (payload, { id: notifId }) => {
            const { Message: messages = [] } = this.store.insert(payload, { html: true });
            const [message] = messages;
            const inbox = this.store.inbox;
            if (notifId > inbox.counter_bus_id) {
                inbox.counter++;
            }
            inbox.messages.add(message);
            if (message.thread && notifId > message.thread.message_needaction_counter_bus_id) {
                message.thread.message_needaction_counter++;
            }
            this.store.env.services["mail.out_of_focus"].notify(message);
        });
        this.busService.subscribe("mail.message/mark_as_read", (payload, { id: notifId }) => {
            const { message_ids: messageIds, needaction_inbox_counter } = payload;
            const inbox = this.store.inbox;
            for (const messageId of messageIds) {
                // We need to ignore all not yet known messages because we don't want them
                // to be shown partially as they would be linked directly to cache.
                // Furthermore, server should not send back all messageIds marked as read
                // but something like last read messageId or something like that.
                // (just imagine you mark 1000 messages as read ... )
                const message = this.store.Message.get(messageId);
                if (!message) {
                    continue;
                }
                // update thread counter (before removing message from Inbox, to ensure isNeedaction check is correct)
                const thread = message.thread;
                if (
                    thread &&
                    message.needaction &&
                    notifId > thread.message_needaction_counter_bus_id
                ) {
                    thread.message_needaction_counter--;
                }
                // move messages from Inbox to history
                message.needaction = false;
                inbox.messages.delete({ id: messageId });
                const history = this.store.history;
                history.messages.add(message);
            }
            if (notifId > inbox.counter_bus_id) {
                inbox.counter = needaction_inbox_counter;
                inbox.counter_bus_id = notifId;
            }
            if (inbox.counter > inbox.messages.length) {
                inbox.fetchMoreMessages();
            }
        });
        this.busService.start();
    }
}

export const mailCoreWeb = {
    dependencies: ["bus_service", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const mailCoreWeb = reactive(new MailCoreWeb(env, services));
        mailCoreWeb.setup();
        return mailCoreWeb;
    },
};

registry.category("services").add("mail.core.web", mailCoreWeb);
