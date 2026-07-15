import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/export";
import { useSequential } from "@mail/utils/common/hooks";

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { createElementWithContent } from "@web/core/utils/html";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.channel = fields.One("discuss.channel", {
            inverse: "thread",
            /** @this {import("models").Thread} */
            compute() {
                return this.model === "discuss.channel" ? this.id : undefined;
            },
        });
        this.firstUnreadMessage = fields.One("mail.message", {
            compute() {
                return this.channel?.firstUnreadMessage;
            },
            inverse: "threadAsFirstUnread",
        });
        this.markReadSequential = useSequential();
        this.markingAsRead = false;
        this.scrollUnread = true;
    },
    /** @override */
    async checkReadAccess() {
        const res = await super.checkReadAccess();
        if (!res && this.channel) {
            // channel is assumed to be readable if its channel_type is known
            return this.channel.channel_type;
        }
        return res;
    },
    /**
     * Executes a mark as read after it was requested, possibly queued behind
     * an in-flight one: re-validates against the current state before the RPC.
     *
     * @param {import("models").Message} newestPersistentMessage message to mark
     *  as read, captured when the mark as read was requested
     * @param {boolean} wasMarkedAsUnread whether the channel was marked as
     *  unread when the mark as read was requested
     */
    async handleMarkAsRead(newestPersistentMessage, wasMarkedAsUnread) {
        if (!this.channel?.self_member_id || this.isReadBySelf(newestPersistentMessage)) {
            return;
        }
        if (!wasMarkedAsUnread && this.channel.markedAsUnread) {
            // The user marked the channel as unread after this mark as read
            // was requested: executing it now would revert that more recent
            // explicit action.
            return;
        }
        this.markingAsRead = true;
        return this.markAsReadRpc(newestPersistentMessage);
    },
    /** @param {import("models").Message} message */
    isReadBySelf(message) {
        return (
            this.channel?.self_member_id?.seen_message_id?.id >= message.id &&
            this.channel?.self_member_id?.new_message_separator > message.id
        );
    },
    get isUnread() {
        return this.channel?.self_member_id?.message_unread_counter > 0 || super.isUnread;
    },
    /** @override */
    markAsRead() {
        super.markAsRead(...arguments);
        if (!this.channel?.self_member_id) {
            return;
        }
        // Captured at request time: newer messages have not been validated as
        // read by the caller, their own triggers request another mark as read.
        const newestPersistentMessage = this.newestPersistentOfAllMessage;
        if (!newestPersistentMessage) {
            return;
        }
        if (this.isReadBySelf(newestPersistentMessage)) {
            return;
        }
        const wasMarkedAsUnread = this.channel.markedAsUnread;
        this.markReadSequential(() =>
            this.handleMarkAsRead(newestPersistentMessage, wasMarkedAsUnread)
        ).then(() => (this.markingAsRead = false));
    },
    /** @param {import("models").Message} newestPersistentMessage */
    markAsReadRpc(newestPersistentMessage) {
        return rpc(
            "/discuss/channel/mark_as_read",
            {
                channel_id: this.id,
                last_message_id: newestPersistentMessage.id,
            },
            { silent: true }
        ).catch((e) => {
            if (e.code !== 404) {
                throw e;
            }
        });
    },
    /** @override */
    get needactionCounter() {
        return this.channel?.isChatChannel
            ? this.channel.self_member_id?.message_unread_counter ?? 0
            : super.needactionCounter;
    },
    /** @override */
    open(options) {
        if (this.channel) {
            const res = this.channel.openChannel();
            if (res) {
                return res;
            }
            this.openChatWindow(options);
            return true;
        }
        return super.open(...arguments);
    },
    /** @param {string} body */
    async post(body) {
        const textContent = createElementWithContent("div", body).textContent.trim();
        if (this.channel && textContent.startsWith("/")) {
            const [firstWord] = textContent.substring(1).split(/\s/);
            const command = commandRegistry.get(firstWord, false);
            if (
                command &&
                (!command.condition ||
                    command.condition({ store: this.store, channel: this.channel }))
            ) {
                await this.channel.executeCommand(command, textContent);
                return;
            }
        }
        return super.post(...arguments);
    },
};
patch(Thread.prototype, threadPatch);
