import { BusPlugin } from "@bus/services/bus_plugin";
import { PresencePlugin } from "@bus/services/presence_plugin";
import { StorePlugin } from "@mail/core/common/store_plugin";
import { ChannelMember } from "@mail/discuss/core/common/channel_member_model";

import { Plugin, usePlugin } from "@odoo/owl";

import { GlobalBusPlugin } from "@web/core/global_bus_plugin";
import { services } from "@web/core/services";

export class DiscussCoreCommonPlugin extends Plugin {
    /** Started with the store it uses (see `StorePlugin`). */
    static sequence = 110;

    #busService = usePlugin(BusPlugin);
    #bus = usePlugin(GlobalBusPlugin).bus;
    #presence = usePlugin(PresencePlugin);
    store = usePlugin(StorePlugin);

    setup() {
        this.#busService.subscribe("discuss.channel/delete", (payload, metadata) => {
            const channel = this.store["discuss.channel"].insert(payload.id);
            this._handleNotificationChannelDelete(channel, metadata);
        });
        this.#busService.subscribe("discuss.channel/new_message", (payload, metadata) => {
            this.store.insert(payload.store_data);
            this._handleNotificationNewMessage(payload, metadata);
        });
        this.#bus.addEventListener("mail.message/delete", ({ detail: { message, notifId } }) => {
            const self_member_id = message.channel_id?.self_member_id;
            if (self_member_id) {
                if (
                    self_member_id &&
                    message.id > (self_member_id.seen_message_id?.id ?? 0) &&
                    notifId > self_member_id.message_unread_counter_bus_id
                ) {
                    self_member_id.message_unread_counter--;
                }
            }
        });
        this.store.onChange(
            () => [this.#presence.isOdooFocused()],
            (isOdooFocused) => {
                if (isOdooFocused) {
                    return;
                }
                const timeout = setTimeout(
                    () => this.hideReadNewMessageSeparators(),
                    ChannelMember.NEW_MESSAGE_SEPARATOR_STALE_DELAY
                );
                return () => clearTimeout(timeout);
            },
            { immediate: true }
        );
    }

    /**
     * Hide the new message separators of the displayed channels that only mark
     * read messages, as the user has been away from Odoo for a while.
     */
    async hideReadNewMessageSeparators() {
        await this.store.chatHub.initPromise;
        for (const channel of this.store.displayedChannels) {
            channel.self_member_id?.hideReadNewMessageSeparatorUi();
        }
    }

    /**
     * @param {import("models").DiscussChannel} channel
     * @param {{ notifId: number}} metadata
     */
    async _handleNotificationChannelDelete(channel, _metadata) {
        await channel.closeChatWindow();
        channel.messages.splice(0, channel.messages.length);
        this.#bus.trigger("discuss.channel/delete", { channel });
        channel.delete();
    }

    async _handleNotificationNewMessage(payload, { id: notifId }) {
        const { store_data, id: channelId, silent, temporary_id } = payload;
        const channel = await this.store["discuss.channel"].getOrFetch(channelId);
        if (!channel) {
            return;
        }
        await this.store.chatHub.initPromise;
        const message = this.store["mail.message"].get(store_data["mail.message"][0]);
        if (!message) {
            return;
        }
        if (message.notIn(channel.messages)) {
            if (!channel.loadNewer) {
                channel.addOrReplaceMessage(message, this.store["mail.message"].get(temporary_id));
            } else if (channel.status === "loading") {
                channel.pendingNewMessages.push(message);
            }
            if (message.isSelfAuthored) {
                channel.onNewSelfMessage(message);
            } else {
                if (channel.self_member_id?.shouldMoveNewMessageSeparatorUi(message)) {
                    channel.self_member_id.new_message_separator_ui = message.id;
                }
                if (!channel.isDisplayed && channel.self_member_id) {
                    channel.scrollUnread = true;
                }
                if (
                    notifId > channel.self_member_id?.message_unread_counter_bus_id &&
                    (!message.isNotification ||
                        (message.subtype_id === this.store.mt_important_notification &&
                            message.thread?.channel))
                ) {
                    channel.self_member_id.message_unread_counter++;
                }
                if (channel.shouldTranslateNewMessages) {
                    message.toggleTranslation();
                }
            }
        }
        if (
            message.notificationType === "meeting_to_group_chat" &&
            this.store.discuss.thread?.channel?.eq(channel)
        ) {
            this.store.discuss.sidebarState.activeTab = channel.primaryMessagingMenuTab;
        }
        if (
            !channel.loadNewer &&
            !message.isSelfAuthored &&
            channel.scrollTop === "bottom" &&
            channel.composer.isFocused &&
            this.store.self_user &&
            channel.newestPersistentMessage?.eq(channel.newestMessage) &&
            !channel.markedAsUnread
        ) {
            channel.markAsRead();
        }
        this.#bus.trigger("discuss.channel/new_message", { channel, message, silent });
        const authorMember = channel.channel_member_ids.find((member) =>
            member.persona?.eq(message.author)
        );
        if (authorMember) {
            authorMember.seen_message_id = message;
        }
    }
}

services.add(DiscussCoreCommonPlugin);
