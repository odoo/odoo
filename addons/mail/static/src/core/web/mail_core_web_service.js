/* @odoo-module */

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
        this.rpc = services.rpc;
        this.store = services["mail.store"];
    }

    setup() {
        this.messagingService.isReady.then(() => {
            this.rpc("/mail/load_message_failures", {}, { silent: true }).then((messages) => {
                this.store.Message.insert(messages, { html: true });
            });
            this.busService.subscribe("mail.activity/updated", (payload) => {
                if (payload.activity_created) {
                    this.store.activityCounter++;
                }
                if (payload.activity_deleted) {
                    this.store.activityCounter--;
                }
            });
            this.env.bus.addEventListener("mail.message/delete", ({ detail: { message } }) => {
                if (message.isNeedaction) {
                    this.store.discuss.inbox.counter--;
                }
                if (message.isStarred) {
                    this.store.discuss.starred.counter--;
                }
            });
            this.busService.subscribe("mail.message/inbox", (payload) => {
                const message = this.store.Message.insert(payload, { html: true });
                const inbox = this.store.discuss.inbox;
                if (message.notIn(inbox.messages)) {
                    inbox.counter++;
                }
                inbox.messages.add(message);
                const thread = message.originThread;
                if (message.notIn(thread.needactionMessages)) {
                    thread.message_needaction_counter++;
                }
                thread.needactionMessages.add(message);
            });
            this.busService.subscribe("mail.message/mark_as_read", (payload) => {
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
                    const originThread = message.originThread;
                    if (originThread && message.isNeedaction) {
                        originThread.message_needaction_counter--;
                        originThread.needactionMessages.delete({ id: messageId });
                    }
                    // move messages from Inbox to history
                    const partnerIndex = message.needaction_partner_ids.find(
                        (p) => p === this.store.user?.id
                    );
                    const index = message.needaction_partner_ids.indexOf(partnerIndex);
                    if (index >= 0) {
                        message.needaction_partner_ids.splice(index, 1);
                    }
                    inbox.messages.delete({ id: messageId });
                    const history = this.store.discuss.history;
                    history.messages.add(message);
                }
                inbox.counter = needaction_inbox_counter;
                if (inbox.counter > inbox.messages.length) {
                    this.threadService.fetchMoreMessages(inbox);
                }
            });
            this.busService.start();
        });
    }
}

export const mailCoreWeb = {
    dependencies: [
        "bus_service",
        "mail.message",
        "mail.messaging",
        "mail.store",
        "rpc",
        "mail.thread",
    ],
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
