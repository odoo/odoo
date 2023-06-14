/* @odoo-module */

import { insertMessage } from "@mail/core/common/message_service";
import { markup, reactive, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const OTHER_LONG_TYPING = 60000;

let busService;
/** @type {Map<number, number>} */
let channelIdByMessageId;
/** @type {Map<number, string>} */
let loadStateByChannelId;
/** @type {Map<number, Set<number>>} */
let messageIdsByChannelId;
let ormService;
/** @type {Map<number, string>} */
let pinnedAtByMessageId;
let rpcService;
/** @type {import("@mail/core/common/store_service").Store} */
let storeService;

/**
 * @param {number} channelId
 * @param {number} messageId
 * @param {string} pinnedAt
 */
export function addPinnedMessage(channelId, messageId, pinnedAt) {
    if (!messageIdsByChannelId.has(channelId)) {
        messageIdsByChannelId.set(channelId, new Set());
    }
    const messageIds = messageIdsByChannelId.get(channelId);
    messageIds.add(messageId);
    channelIdByMessageId.set(messageId, channelId);
    pinnedAtByMessageId.set(messageId, pinnedAt);
}

/**
 * @param {import("@mail/core/common/thread_model").Thread} channel
 */
export async function fetchPinnedMessages(channel) {
    if (
        channel.model !== "discuss.channel" ||
        ["loaded", "loading"].includes(loadStateByChannelId.get(channel.id))
    ) {
        return;
    }
    loadStateByChannelId.set(channel.id, "loading");
    try {
        const messagesData = await rpcService("/discuss/channel/pinned_messages", {
            channel_id: channel.id,
        });
        messagesData.forEach((messageData) => {
            if (messageData.parentMessage) {
                messageData.parentMessage.body = markup(messageData.parentMessage.body);
            }
            messageData.body = markup(messageData.body);
            insertMessage(messageData);
        });
        loadStateByChannelId.set(channel.id, "loaded");
    } catch (e) {
        loadStateByChannelId.set(channel.id, "error");
        throw e;
    }
}

/**
 * @param {number} messageId
 * @returns {string|null}
 */
export function getMessagePinnedAt(messageId) {
    const pinnedAt = pinnedAtByMessageId.get(messageId);
    return pinnedAt ? luxon.DateTime.fromISO(new Date(pinnedAt).toISOString()) : null;
}

/**
 * @param {import("@mail/core/common/thread_model").Thread} channel
 * @returns {import("@mail/core/common/message_model").Message[]}
 */
export function getPinnedMessages(channel) {
    return [...(messageIdsByChannelId.get(channel.id) ?? new Set())]
        .map((id) => insertMessage({ id }))
        .sort((a, b) => {
            const aPinnedAt = pinnedAtByMessageId.get(a.id);
            const bPinnedAt = pinnedAtByMessageId.get(b.id);
            if (aPinnedAt === bPinnedAt) {
                return b.id - a.id;
            }
            return aPinnedAt < bPinnedAt ? 1 : -1;
        });
}

/**
 * @param {import("@mail/core/common/thread_model").Thread} channel
 * @returns {boolean}
 */
export function hasPinnedMessages(channel) {
    return getPinnedMessages(channel).length > 0;
}

/**
 * @param {number} messageId
 */
export function removePinnedMessage(messageId) {
    const channelId = channelIdByMessageId.get(messageId);
    if (!channelId) {
        return;
    }
    const messageIds = messageIdsByChannelId.get(channelId);
    if (messageIds) {
        messageIds.delete(messageId);
        if (messageIds.size === 0) {
            messageIdsByChannelId.delete(channelId);
        }
    }
    channelIdByMessageId.delete(messageId);
    pinnedAtByMessageId.delete(messageId);
}

/**
 * @param {import("@mail/core/common/message_model").Message}
 * @param {boolean} pinned
 */
export function setPinOnMessage(message, pinned) {
    ormService.call("discuss.channel", "set_message_pin", [message.originThread.id], {
        message_id: message.id,
        pinned,
    });
}

/**
 * @param {import("@mail/core/common/message_model").Message}
 * @param {Object} data
 */
function _onMessageUpdate(message, { pinned_at: pinnedAt }) {
    if (
        message.originThread?.model === "discuss.channel" &&
        (pinnedAt !== undefined || message.isEmpty)
    ) {
        if (pinnedAt && !message.isEmpty) {
            addPinnedMessage(message.originThread.id, message.id, pinnedAt);
        } else {
            removePinnedMessage(message.id);
        }
    }
}

export class MessagePin {
    constructor(env, services) {
        busService = services.bus_service;
        ormService = services.orm;
        rpcService = services.rpc;
        storeService = services["mail.store"];
        Object.assign(this, {
            busService,
            env,
            ormService,
            rpcService,
            storeService,
        });
    }

    setup() {
        loadStateByChannelId = new Map();
        messageIdsByChannelId = new Map();
        channelIdByMessageId = new Map();
        pinnedAtByMessageId = new Map();
        this.env.bus.addEventListener("mail.message/onUpdate", ({ detail: { message, data } }) => {
            _onMessageUpdate(message, data);
        });
        busService.subscribe("mail.message/delete", ({ message_ids }) => {
            for (const messageId of message_ids) {
                removePinnedMessage(messageId);
            }
        });
        busService.start();
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
