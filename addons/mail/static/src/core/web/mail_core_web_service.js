/* @odoo-module */

import { removeFromArray, removeFromArrayWithPredicate } from "@mail/utils/common/arrays";

import { markup, reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class MailCoreWeb {
    constructor(env, services) {
        /** @type {import("@web/env").OdooEnv} */
        this.env = env;
        /** @type {ReturnType<typeof import("@bus/services/bus_service").busService.start>} */
        this.busService = services["bus_service"];
        /** @type {import("@mail/core/common/message_service").MessageService} */
        this.messageService = services["mail.message"];
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        this.messagingService = services["mail.messaging"];
        /** @type {ReturnType<typeof import("@web/core/network/rpc_service").rpcService.start>} */
        this.rpc = services.rpc;
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
    }

    setup() {
        this.messagingService.isReady.then(() => {
            this.rpc("/mail/load_message_failures", {}, { silent: true }).then((messages) => {
                messages.map((messageData) =>
                    this.messageService.insert({
                        ...messageData,
                        body: messageData.body ? markup(messageData.body) : messageData.body,
                        // implicit: failures are sent by the server at
                        // initialization only if the current partner is
                        // author of the message
                        author: this.store.user,
                    })
                );
                this.store.notificationGroups.sort(
                    (n1, n2) => n2.lastMessage.id - n1.lastMessage.id
                );
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
                    removeFromArrayWithPredicate(
                        this.store.discuss.inbox.messages,
                        ({ id }) => id === message.id
                    );
                    this.store.discuss.inbox.counter--;
                }
                if (message.isStarred) {
                    removeFromArrayWithPredicate(
                        this.store.discuss.starred.messages,
                        ({ id }) => id === message.id
                    );
                    this.store.discuss.starred.counter--;
                }
                if (message.originThread) {
                    if (message.isNeedaction) {
                        removeFromArrayWithPredicate(
                            message.originThread.needactionMessages,
                            ({ id }) => id === message.id
                        );
                    }
                }
            });
            this.busService.subscribe("mail.message/inbox", (payload) => {
                const data = Object.assign(payload, { body: markup(payload.body) });
                const message = this.messageService.insert(data);
                const inbox = this.store.discuss.inbox;
                if (!inbox.messages.includes(message)) {
                    inbox.messages.push(message);
                    inbox.counter++;
                }
                const thread = message.originThread;
                if (!thread.needactionMessages.includes(message)) {
                    thread.needactionMessages.push(message);
                    thread.message_needaction_counter++;
                }
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
                    const message = this.store.messages[messageId];
                    if (!message) {
                        continue;
                    }
                    // update thread counter (before removing message from Inbox, to ensure isNeedaction check is correct)
                    const originThread = message.originThread;
                    if (originThread && message.isNeedaction) {
                        originThread.message_needaction_counter--;
                        removeFromArrayWithPredicate(
                            originThread.needactionMessages,
                            ({ id }) => id === messageId
                        );
                    }
                    // move messages from Inbox to history
                    const partnerIndex = message.needaction_partner_ids.find(
                        (p) => p === this.store.user?.id
                    );
                    removeFromArray(message.needaction_partner_ids, partnerIndex);
                    removeFromArrayWithPredicate(inbox.messages, ({ id }) => id === messageId);
                    const history = this.store.discuss.history;
                    if (!history.messages.includes(message)) {
                        history.messages.push(message);
                    }
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
    dependencies: ["bus_service", "mail.message", "mail.messaging", "mail.store", "rpc"],
    start(env, services) {
        const mailCoreWeb = reactive(new MailCoreWeb(env, services));
        mailCoreWeb.setup();
        return mailCoreWeb;
    },
};

registry.category("services").add("mail.core.web", mailCoreWeb);
