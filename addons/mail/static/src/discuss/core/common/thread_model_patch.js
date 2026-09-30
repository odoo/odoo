import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/export";
import { useSequential } from "@mail/utils/common/hooks";

import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { createElementWithContent } from "@web/core/utils/html";
import { patch } from "@web/core/utils/patch";

const commandRegistry = registry.category("discuss.channel_commands");
// Past this delay, consumers stop waiting on the prefetch rather than delaying the user further.
const PREFETCH_MAX_WAIT = 200;

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
        // Send the mark as read and the mark as unread one at a time: the server
        // applies them in the order it receives them, not the order they are sent.
        this.markReadSequential = useSequential();
        this.markingAsRead = false;
        /** @type {Promise|undefined} resolves when the prefetch is done or after PREFETCH_MAX_WAIT */
        this.prefetching = undefined;
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
     */
    async handleMarkAsRead(newestPersistentMessage) {
        if (!this.channel?.self_member_id || this.isReadBySelf(newestPersistentMessage)) {
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
    async loadAround() {
        if (this.prefetching) {
            // Would be skipped while the prefetch is loading.
            await this.prefetching;
        }
        return super.loadAround(...arguments);
    },
    /** @override */
    async fetchInitialMessages({ routeParams = {} } = {}) {
        if (this.channel?.self_member_id && this.scrollUnread) {
            return this.loadAround({
                messageId: this.channel.self_member_id.new_message_separator,
                routeParams,
            });
        }
        return super.fetchInitialMessages(...arguments);
    },
    async prefetchMessages() {
        // Only members are kept up to date by the bus once loaded.
        if (!this.channel?.self_member_id || this.status === "loading") {
            return;
        }
        const fetching = this.fetchInitialMessages({ routeParams: { is_prefetch: true } });
        this.prefetching = Promise.race([
            fetching,
            new Promise((resolve) => setTimeout(resolve, PREFETCH_MAX_WAIT)),
        ]);
        await fetching;
        this.prefetching = undefined;
        if (this.hasLoadingFailed && !this.channel.isDisplayed) {
            // Retry on open instead of showing an error for a thread the user never opened.
            this.hasLoadingFailed = false;
            this.hasLoadingFailedError = undefined;
            this.isLoaded = false;
            this.status = "new";
        }
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
        this.markReadSequential(() => this.handleMarkAsRead(newestPersistentMessage)).then(
            () => (this.markingAsRead = false)
        );
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
