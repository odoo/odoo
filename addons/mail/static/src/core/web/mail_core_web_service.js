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
        this.threadService = services["mail.thread"];
        this.messageService = services["mail.message"];
        this.messagingService = services["mail.messaging"];
        this.store = services["mail.store"];
    }

    setup() {
        this.busService.subscribe("mail.activity/updated", (payload, { id: notifId }) => {
            if (payload.activity_created && notifId > this.store.activity_counter_bus_id) {
                this.store.activityCounter++;
            }
            if (payload.activity_deleted && notifId > this.store.activity_counter_bus_id) {
                this.store.activityCounter--;
            }
        });
        this.env.bus.addEventListener("mail.message/delete", ({ detail: { message, notifId } }) => {
            if (message.isNeedaction && notifId > this.store.discuss.inbox.counter_bus_id) {
                this.store.discuss.inbox.counter--;
            }
            if (message.isStarred && notifId > this.store.discuss.starred.counter_bus_id) {
                this.store.discuss.starred.counter--;
            }
        });
        this.busService.subscribe("mail.message/inbox", (payload, { id: notifId }) => {
            let message = this.store.Message.get(payload.id);
            const alreadyInNeedaction = message?.in(message.thread.needactionMessages);
            message = this.store.Message.insert(payload, { html: true });
            const inbox = this.store.discuss.inbox;
            if (notifId > inbox.counter_bus_id) {
                inbox.counter++;
            }
            inbox.messages.add(message);
            if (
                !alreadyInNeedaction &&
                notifId > message.thread.message_needaction_counter_bus_id
            ) {
                message.thread.message_needaction_counter++;
            }
        });
        this.busService.subscribe("mail.message/mark_as_read", (payload, { id: notifId }) => {
            const { message_ids: messageIds, needaction_inbox_counter } = payload;
            const inbox = this.store.discuss.inbox;
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
                    message.isNeedaction &&
                    notifId > thread.message_needaction_counter_bus_id
                ) {
                    thread.message_needaction_counter--;
                }
                // move messages from Inbox to history
                const partnerIndex = message.needaction_partner_ids.find(
                    (p) => p === this.store.self.id
                );
                const index = message.needaction_partner_ids.indexOf(partnerIndex);
                if (index >= 0) {
                    message.needaction_partner_ids.splice(index, 1);
                }
                inbox.messages.delete({ id: messageId });
                const history = this.store.discuss.history;
                history.messages.add(message);
            }
            if (notifId > inbox.counter_bus_id) {
                inbox.counter = needaction_inbox_counter;
                inbox.counter_bus_id = notifId;
            }
            if (inbox.counter > inbox.messages.length) {
                this.threadService.fetchMoreMessages(inbox);
            }
        });
        this.busService.start();
    }
}

export const mailCoreWeb = {
    dependencies: ["bus_service", "mail.message", "mail.messaging", "mail.store", "mail.thread"],
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
