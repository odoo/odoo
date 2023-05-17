/* @odoo-module */

import { markup, reactive, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const OTHER_LONG_TYPING = 60000;

export class MessagePin {
    busService;
    /** @type {import("@mail/core/message_service").MessageService} */
    messageService;
    /** @type {Map<number, string>} */
    loadStateByChannelId = new Map();
    /** @type {Map<number, Set<number>>} */
    messageIdsByChannelId = new Map();
    /** @type {Map<number, number>} */
    channelIdByMessageId = new Map();
    /** @type {Map<number, string>} */
    pinnedAtByMessageId = new Map();
    /** @type {import("@mail/core/store_service").Store} */
    storeService;

    constructor(
        env,
        {
            bus_service: busService,
            "mail.message": messageService,
            "mail.store": storeService,
            orm: ormService,
            rpc: rpcService,
        }
    ) {
        Object.assign(this, {
            busService,
            env,
            messageService,
            ormService,
            rpcService,
            storeService,
        });
    }

    setup() {
        this.env.bus.addEventListener("mail.message/onUpdate", ({ detail: { message, data } }) => {
            this.onMessageUpdate(message, data);
        });
        this.busService.subscribe("mail.message/delete", ({ message_ids }) => {
            for (const messageId of message_ids) {
                this.removePinnedMessage(messageId);
            }
        });
        this.busService.start();
    }

    /**
     * @param {number} channelId
     * @param {number} messageId
     * @param {string} pinnedAt
     */
    addPinnedMessage(channelId, messageId, pinnedAt) {
        if (!this.messageIdsByChannelId.has(channelId)) {
            this.messageIdsByChannelId.set(channelId, new Set());
        }
        const messageIds = this.messageIdsByChannelId.get(channelId);
        messageIds.add(messageId);
        this.channelIdByMessageId.set(messageId, channelId);
        this.pinnedAtByMessageId.set(messageId, pinnedAt);
    }

    /**
     * @param {import("@mail/core/thread_model").Thread} channel
     */
    async fetchPinnedMessages(channel) {
        if (
            channel.model !== "discuss.channel" ||
            ["loaded", "loading"].includes(this.loadStateByChannelId.get(channel.id))
        ) {
            return;
        }
        this.loadStateByChannelId.set(channel.id, "loading");
        try {
            const messagesData = await this.rpcService("/discuss/channel/pinned_messages", {
                channel_id: channel.id,
            });
            messagesData.forEach((messageData) => {
                if (messageData.parentMessage) {
                    messageData.parentMessage.body = markup(messageData.parentMessage.body);
                }
                messageData.body = markup(messageData.body);
                this.messageService.insert(messageData);
            });
            this.loadStateByChannelId.set(channel.id, "loaded");
        } catch (e) {
            this.loadStateByChannelId.set(channel.id, "error");
            throw e;
        }
    }

    /**
     * @param {number} messageId
     * @returns {string|null}
     */
    getPinnedAt(messageId) {
        const pinnedAt = this.pinnedAtByMessageId.get(messageId);
        return pinnedAt ? luxon.DateTime.fromISO(new Date(pinnedAt).toISOString()) : null;
    }

    /**
     * @param {import("@mail/core/thread_model").Thread} channel
     * @returns {import("@mail/core/message_model").Message[]}
     */
    getPinnedMessages(channel) {
        return [...(this.messageIdsByChannelId.get(channel.id) ?? new Set())]
            .map((id) => this.messageService.insert({ id }))
            .sort((a, b) => {
                const aPinnedAt = this.pinnedAtByMessageId.get(a.id);
                const bPinnedAt = this.pinnedAtByMessageId.get(b.id);
                if (aPinnedAt === bPinnedAt) {
                    return b.id - a.id;
                }
                return aPinnedAt < bPinnedAt ? 1 : -1;
            });
    }

    /**
     * @param {import("@mail/core/thread_model").Thread} channel
     * @returns {boolean}
     */
    hasPinnedMessages(channel) {
        return this.getPinnedMessages(channel).length > 0;
    }

    /**
     * @param {import("@mail/core/message_model").Message}
     * @param {Object} data
     */
    onMessageUpdate(message, { pinned_at: pinnedAt }) {
        if (
            message.originThread?.model === "discuss.channel" &&
            (pinnedAt !== undefined || message.isEmpty)
        ) {
            if (pinnedAt && !message.isEmpty) {
                this.addPinnedMessage(message.originThread.id, message.id, pinnedAt);
            } else {
                this.removePinnedMessage(message.id);
            }
        }
    }

    /**
     * @param {number} messageId
     */
    removePinnedMessage(messageId) {
        const channelId = this.channelIdByMessageId.get(messageId);
        if (!channelId) {
            return;
        }
        const messageIds = this.messageIdsByChannelId.get(channelId);
        if (messageIds) {
            messageIds.delete(messageId);
            if (messageIds.size === 0) {
                this.messageIdsByChannelId.delete(channelId);
            }
        }
        this.channelIdByMessageId.delete(messageId);
        this.pinnedAtByMessageId.delete(messageId);
    }

    /**
     * @param {import("@mail/core/message_model").Message}
     * @param {boolean} pinned
     */
    setPin(message, pinned) {
        this.ormService.call("discuss.channel", "set_message_pin", [message.originThread.id], {
            message_id: message.id,
            pinned,
        });
    }
}

export const messagePinService = {
    dependencies: ["bus_service", "mail.message", "mail.store", "orm", "rpc"],
    start(env, services) {
        const messagePin = reactive(new MessagePin(env, services));
        messagePin.setup();
        return messagePin;
    },
};

registry.category("services").add("discuss.message.pin", messagePinService);

/**
 * @returns {MessagePin}
 * */
export function useMessagePinService() {
    return useState(useService("discuss.message.pin"));
}
