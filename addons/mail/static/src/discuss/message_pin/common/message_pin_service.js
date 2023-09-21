/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { MessageConfirmDialog } from "@mail/core/common/message_confirm_dialog";
import { Message as MessageModel } from "@mail/core/common/message_model";
import { Thread } from "@mail/core/common/thread_model";

import { markup, reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export const OTHER_LONG_TYPING = 60000;

patch(Thread.prototype, {
    setup() {
        super.setup();
        /** @type {'loaded'|'loading'|'error'|undefined} */
        this.pinnedMessagesState = undefined;
        this.pinnedMessages = Thread.Set("Message");
    },
});

patch(MessageModel.prototype, {
    setup() {
        super.setup();
        /** @type {string} */
        this.pinnedAt = undefined;
    },
});

export class MessagePin {
    busService;
    /** @type {import("@mail/core/common/store_service").Store} */
    store;

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.dialogService = services.dialog;
        this.ormService = services.orm;
        this.rpcService = services.rpc;
        this.store = services["mail.store"];
    }

    setup() {
        this.env.bus.addEventListener("mail.message/onUpdate", ({ detail: { message, data } }) => {
            this.onMessageUpdate(message, data);
        });
        this.busService.start();
    }

    /**
     * @param {import("models").Thread} channel
     */
    async fetchPinnedMessages(channel) {
        if (
            channel.model !== "discuss.channel" ||
            ["loaded", "loading"].includes(channel.pinnedMessagesState)
        ) {
            return;
        }
        channel.pinnedMessagesState = "loading";
        try {
            const messagesData = await this.rpcService("/discuss/channel/pinned_messages", {
                channel_id: channel.id,
            });
            messagesData.forEach((messageData) => {
                if (messageData.parentMessage) {
                    messageData.parentMessage.body = markup(messageData.parentMessage.body);
                }
                messageData.body = markup(messageData.body);
                this.store.Message.insert(messageData);
            });
            channel.pinnedMessagesState = "loaded";
        } catch (e) {
            channel.pinnedMessagesState = "error";
            throw e;
        }
    }

    /**
     * @param {number} messageId
     * @returns {string|null}
     */
    getPinnedAt(messageId) {
        const pinnedAt = this.store.Message.get(messageId)?.pinnedAt;
        return pinnedAt ? luxon.DateTime.fromISO(new Date(pinnedAt).toISOString()) : null;
    }

    /**
     * @param {import("models").Thread} channel
     * @returns {import("models").Message[]}
     */
    getPinnedMessages(channel) {
        return [...channel.pinnedMessages].sort((a, b) => {
            if (a.pinnedAt === b.pinnedAt) {
                return b.id - a.id;
            }
            return a.pinnedAt < b.pinnedAt ? 1 : -1;
        });
    }

    /**
     * @param {import("models).Thread} channel
     * @returns {boolean}
     */
    hasPinnedMessages(channel) {
        return this.getPinnedMessages(channel).length > 0;
    }

    /**
     * @param {import("models").Message}
     * @param {Object} data
     */
    onMessageUpdate(message, { pinned_at: pinnedAt }) {
        if (
            message.originThread?.model === "discuss.channel" &&
            (pinnedAt !== undefined || message.isEmpty)
        ) {
            if (pinnedAt && !message.isEmpty) {
                message.originThread.pinnedMessages.add(message);
                message.pinnedAt = pinnedAt;
            } else {
                delete message.pinnedAt;
                message.originThread.pinnedMessages.delete(message);
            }
        }
    }

    /**
     * Prompts the user for confirmation, then sets pinned to true.
     *
     * @param {import("models").Message}
     */
    pin(message) {
        const thread = message.originThread;
        this.dialogService.add(MessageConfirmDialog, {
            confirmText: _t("Yeah, pin it!"),
            message: message,
            messageComponent: Message,
            prompt: _t("You sure want this message pinned to %(conversation)s forever and ever?", {
                conversation: thread.prefix + thread.displayName,
            }),
            size: "md",
            title: _t("Pin It"),
            onConfirm: () => this.setPin(message, true),
        });
    }

    /**
     * @param {import("models").Message}
     * @param {boolean} pinned
     */
    setPin(message, pinned) {
        this.ormService.call("discuss.channel", "set_message_pin", [message.originThread.id], {
            message_id: message.id,
            pinned,
        });
    }

    /**
     * Prompts the user for confirmation, then sets pinned to false.
     *
     * @param {import("models").Message}
     */
    unpin(message) {
        this.dialogService.add(MessageConfirmDialog, {
            confirmColor: "btn-danger",
            confirmText: _t("Yes, remove it please"),
            message: message,
            messageComponent: Message,
            prompt: _t(
                "Well, nothing lasts forever, but are you sure you want to unpin this message?"
            ),
            size: "md",
            title: _t("Unpin Message"),
            onConfirm: () => this.setPin(message, false),
        });
    }
}

export const messagePinService = {
    dependencies: ["bus_service", "dialog", "mail.store", "orm", "rpc"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const messagePin = reactive(new MessagePin(env, services));
        messagePin.setup();
        return messagePin;
    },
};

registry.category("services").add("discuss.message.pin", messagePinService);
