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
        this.markedAsUnread = false;
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
    get isUnread() {
        return this.channel?.self_member_id?.message_unread_counter > 0 || super.isUnread;
    },
    /** @override */
    markAsRead() {
        super.markAsRead(...arguments);
        if (!this.channel?.self_member_id) {
            return;
        }
        const newestPersistentMessage = this.newestPersistentOfAllMessage;
        if (!newestPersistentMessage) {
            return;
        }
        const alreadyReadBySelf =
            this.channel?.self_member_id.seen_message_id?.id >= newestPersistentMessage.id &&
            this.channel?.self_member_id.new_message_separator > newestPersistentMessage.id;
        if (alreadyReadBySelf) {
            return;
        }
        this.markReadSequential(async () => {
            this.markingAsRead = true;
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
        }).then(() => (this.markingAsRead = false));
    },
    /** @override */
    get needactionCounter() {
        return this.channel?.isChatChannel
            ? this.channel.self_member_id?.message_unread_counter ?? 0
            : super.needactionCounter;
    },
    /** @override */
    onNewSelfMessage(message) {
        if (
            !this.channel?.self_member_id ||
            message.id < this.channel?.self_member_id.seen_message_id?.id
        ) {
            return;
        }
        this.channel.self_member_id.seen_message_id = message;
        this.channel.self_member_id.new_message_separator = message.id + 1;
        this.channel.self_member_id.new_message_separator_ui =
            this.channel?.self_member_id.new_message_separator;
        this.markedAsUnread = false;
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
                (!command.channel_types ||
                    command.channel_types.includes(this.channel?.channel_type))
            ) {
                await this.channel.executeCommand(command, textContent);
                return;
            }
        }
        return super.post(...arguments);
    },
};
patch(Thread.prototype, threadPatch);
