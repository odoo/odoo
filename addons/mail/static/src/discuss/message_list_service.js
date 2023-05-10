/** @odoo-module */

import { markup, toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

const FETCH_LIMIT = 30;

export class MessageListService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        /** @type {import("@mail/core/message_service").MessageService} */
        this.messageService = services["mail.message"];
        this.rpc = services.rpc;
        /** @type {import("@mail/core/store_service").Store} */
        this.store = services["mail.store"];
        /** @type {import("@mail/core/thread_service").ThreadService} */
        this.threadService = services["mail.thread"];
    }

    /**
     * @param {Thread} thread
     * @param {"older"|"newer"} epoch
     */
    async fetchMoreMessages(thread, epoch = "older") {
        if (
            thread.status === "loading" ||
            (epoch === "older" && !thread.loadOlder) ||
            (epoch === "newer" && !thread.loadNewer)
        ) {
            return;
        }
        const before = epoch === "older" ? thread.oldestPersistentMessage?.id : undefined;
        const after = epoch === "newer" ? thread.newestPersistentMessage?.id : undefined;
        try {
            const fetched = await this._fetchMessages(thread, { after, before });
            if (
                (after !== undefined && !thread.messages.some((message) => message.id === after)) ||
                (before !== undefined && !thread.messages.some((message) => message.id === before))
            ) {
                // there might have been a jump to message during RPC fetch.
                // Abort feeding messages as to not put holes in message list.
                return;
            }
            const alreadyKnownMessages = new Set(thread.messages.map(({ id }) => id));
            const messagesToAdd = fetched.filter(
                (message) => !alreadyKnownMessages.has(message.id)
            );
            if (epoch === "older") {
                thread.messages.unshift(...messagesToAdd);
            } else {
                thread.messages.push(...messagesToAdd);
            }
            if (fetched.length < FETCH_LIMIT) {
                if (epoch === "older") {
                    thread.loadOlder = false;
                } else if (epoch === "newer") {
                    thread.loadNewer = false;
                    const missingMessages = thread.pendingNewMessages.filter(
                        ({ id }) => !alreadyKnownMessages.has(id)
                    );
                    if (missingMessages.length > 0) {
                        thread.messages.push(...missingMessages);
                        thread.messages.sort((m1, m2) => m1.id - m2.id);
                    }
                }
            }
        } catch {
            // handled in fetchMessages
        }
        thread.pendingNewMessages = [];
    }

    /**
     * @param {Thread} thread
     */
    async fetchNewMessages(thread) {
        if (
            thread.status === "loading" ||
            (thread.isLoaded && ["discuss.channel", "mail.box"].includes(thread.model))
        ) {
            return;
        }
        const after = thread.isLoaded ? thread.newestPersistentMessage?.id : undefined;
        try {
            const fetched = await this._fetchMessages(thread, { after });
            // feed messages
            // could have received a new message as notification during fetch
            // filter out already fetched (e.g. received as notification in the meantime)
            let startIndex;
            if (after === undefined) {
                startIndex = 0;
            } else {
                const afterIndex = thread.messages.findIndex((message) => message.id === after);
                if (afterIndex === -1) {
                    // there might have been a jump to message during RPC fetch.
                    // Abort feeding messages as to not put holes in message list.
                    return;
                } else {
                    startIndex = afterIndex + 1;
                }
            }
            const alreadyKnownMessages = new Set(thread.messages.map((m) => m.id));
            const filtered = fetched.filter(
                (message) =>
                    !alreadyKnownMessages.has(message.id) &&
                    (thread.persistentMessages.length === 0 ||
                        message.id < thread.oldestPersistentMessage.id ||
                        message.id > thread.newestPersistentMessage.id)
            );
            thread.messages.splice(startIndex, 0, ...filtered);
            // feed needactions
            // same for needaction messages, special case for mailbox:
            // kinda "fetch new/more" with needactions on many origin threads at once
            if (toRaw(thread) === toRaw(this.store.discuss.inbox)) {
                for (const message of fetched) {
                    const thread = message.originThread;
                    if (!thread.needactionMessages.includes(message)) {
                        thread.needactionMessages.unshift(message);
                    }
                }
            } else {
                const startNeedactionIndex =
                    after === undefined
                        ? 0
                        : thread.messages.findIndex((message) => message.id === after);
                const filteredNeedaction = fetched.filter(
                    (message) =>
                        message.isNeedaction &&
                        (thread.needactionMessages.length === 0 ||
                            message.id < thread.oldestNeedactionMessage.id ||
                            message.id > thread.newestNeedactionMessage.id)
                );
                thread.needactionMessages.splice(startNeedactionIndex, 0, ...filteredNeedaction);
            }
            Object.assign(thread, {
                loadOlder:
                    after === undefined && fetched.length === FETCH_LIMIT
                        ? true
                        : after === undefined && fetched.length !== FETCH_LIMIT
                        ? false
                        : thread.loadOlder,
            });
        } catch {
            // handled in fetchMessages
        }
    }

    /**
     * Get ready to jump to a message in a thread. This method will fetch the
     * messages around the message to jump to if required, and update the thread
     * messages accordingly.
     *
     * @param {Message} [messageId] if not provided, load around newest message
     */
    async loadAround(thread, messageId) {
        if (!thread.messages.some(({ id }) => id === messageId)) {
            const messages = await this.rpc(this._getFetchRoute(thread), {
                ...this._getFetchParams(thread),
                around: messageId,
            });
            thread.messages = messages.reverse().map((message) =>
                this.messageService.insert({
                    ...message,
                    body: message.body ? markup(message.body) : message.body,
                })
            );
            thread.loadNewer = true;
            thread.loadOlder = true;
            if (messages.length < FETCH_LIMIT) {
                const olderMessagesCount = messages.filter(({ id }) => id < messageId).length;
                if (olderMessagesCount < FETCH_LIMIT / 2) {
                    thread.loadOlder = false;
                } else {
                    thread.loadNewer = false;
                }
            }
            // Give some time to the UI to update.
            await new Promise((resolve) => setTimeout(() => requestAnimationFrame(resolve)));
        }
    }

    /**
     * @private
     * @param {Thread} thread
     * @param {{after: Number, before: Number}}
     */
    async _fetchMessages(thread, { after, before } = {}) {
        thread.status = "loading";
        if (thread.type === "chatter" && !thread.id) {
            return [];
        }
        try {
            // ordered messages received: newest to oldest
            const rawMessages = await this.rpc(this._getFetchRoute(thread), {
                ...this._getFetchParams(thread),
                limit: FETCH_LIMIT,
                after,
                before,
            });
            const messages = rawMessages.reverse().map((data) => {
                if (data.parentMessage) {
                    data.parentMessage.body = data.parentMessage.body
                        ? markup(data.parentMessage.body)
                        : data.parentMessage.body;
                }
                return this.messageService.insert(
                    Object.assign(data, { body: data.body ? markup(data.body) : data.body })
                );
            });
            this.threadService.update(thread, { isLoaded: true });
            return messages;
        } catch (e) {
            thread.hasLoadingFailed = true;
            throw e;
        } finally {
            thread.status = "ready";
        }
    }

    _getFetchParams(thread) {
        if (thread.model === "discuss.channel") {
            return { channel_id: thread.id };
        }
        if (thread.type === "chatter") {
            return {
                thread_id: thread.id,
                thread_model: thread.model,
            };
        }
        return {};
    }

    _getFetchRoute(thread) {
        if (thread.model === "discuss.channel") {
            return "/discuss/channel/messages";
        }
        switch (thread.type) {
            case "chatter":
                return "/mail/thread/messages";
            case "mailbox":
                return `/mail/${thread.id}/messages`;
            default:
                throw new Error(`Unknown thread type: ${thread.type}`);
        }
    }
}

export const messageListService = {
    dependencies: ["mail.message", "mail.store", "mail.thread", "rpc"],
    start(env, services) {
        return new MessageListService(env, services);
    },
};

registry.category("services").add("discuss.message_list", messageListService);
