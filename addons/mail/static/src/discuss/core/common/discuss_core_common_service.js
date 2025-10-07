import { markup, reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class DiscussCoreCommon {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.busService = services.bus_service;
        this.env = env;
        this.notificationService = services.notification;
        this.orm = services.orm;
        this.presence = services.presence;
        this.store = services["mail.store"];
    }

    setup() {
        this.busService.subscribe("discuss.channel/delete", (payload, metadata) => {
            const thread = this.store["mail.thread"].insert({
                id: payload.id,
                model: "discuss.channel",
            });
            this._handleNotificationChannelDelete(thread, metadata);
        });
        this.busService.subscribe("discuss.channel/new_message", (payload, metadata) => {
            // Insert should always be done before any async operation. Indeed,
            // awaiting before the insertion could lead to overwritting newer
            // state coming from more recent `mail.record/insert` notifications.
            this.store.insert(payload.data);
            this._handleNotificationNewMessage(payload, metadata);
        });
        this.busService.subscribe("discuss.channel/transient_message", (payload) => {
            const { body, channel_id } = payload;
            const lastMessageId = this.store.getLastMessageId();
            const message = this.store["mail.message"].insert({
                author_id: this.store.odoobot,
                body: markup(body),
                id: lastMessageId + 0.01,
                subtype_id: this.store.mt_note,
                is_transient: true,
                thread: { id: channel_id, model: "discuss.channel" },
            });
            message.thread.messages.push(message);
            message.thread.transientMessages.push(message);
        });
        this.busService.subscribe("discuss.channel.member/fetched", (payload) => {
            const { channel_id, id, last_message_id, partner_id } = payload;
            this.store["discuss.channel.member"].insert({
                id,
                fetched_message_id: { id: last_message_id },
                partner_id: { id: partner_id },
                thread: { id: channel_id, model: "discuss.channel" },
            });
        });
        this.env.bus.addEventListener("mail.message/delete", ({ detail: { message, notifId } }) => {
            if (message.thread) {
                const { self_member_id } = message.thread;
                if (
                    message.id > self_member_id?.seen_message_id.id &&
                    notifId > self_member_id.message_unread_counter_bus_id
                ) {
                    self_member_id.message_unread_counter--;
                }
            }
        });
    }

    /**
     * @param {import("models").Thread} thread
     * @param {{ notifId: number}} metadata
     */
    async _handleNotificationChannelDelete(thread, metadata) {
        await thread.closeChatWindow({ force: true });
        thread.messages.splice(0, thread.messages.length);
        thread.delete();
    }

    async _handleNotificationNewMessage(payload, { id: notifId }) {
        const { data, id: channelId, silent, temporary_id } = payload;
        const thread = await this.store["mail.thread"].getOrFetch({
            model: "discuss.channel",
            id: channelId,
        });
        if (!thread) {
            return;
        }
        const message = this.store["mail.message"].get(data["mail.message"][0]);
        if (!message) {
            return;
        }
        if (message.notIn(thread.messages)) {
            if (!thread.loadNewer) {
                thread.addOrReplaceMessage(message, this.store["mail.message"].get(temporary_id));
            } else if (thread.status === "loading") {
                thread.pendingNewMessages.push(message);
            }
            if (message.isSelfAuthored) {
                thread.onNewSelfMessage(message);
            } else {
                if (thread.isDisplayed && thread.self_member_id?.new_message_separator_ui === 0) {
                    thread.self_member_id.new_message_separator_ui = message.id;
                }
                if (!thread.isDisplayed && thread.self_member_id) {
                    thread.scrollUnread = true;
                }
                if (
                    notifId > thread.self_member_id?.message_unread_counter_bus_id &&
                    !message.isNotification
                ) {
                    thread.self_member_id.message_unread_counter++;
                }
            }
        }
        if (
            thread.channel?.channel_type !== "channel" &&
            this.store.self_partner &&
            thread.self_member_id
        ) {
            // disabled on non-channel threads and
            // on "channel" channels for performance reasons
            thread.markAsFetched();
        }
        if (
            !thread.loadNewer &&
            !message.isSelfAuthored &&
            thread.composer.isFocused &&
            this.store.self_partner &&
            thread.newestPersistentMessage?.eq(thread.newestMessage) &&
            !thread.markedAsUnread
        ) {
            thread.markAsRead();
        }
        this.env.bus.trigger("discuss.channel/new_message", { channel: thread, message, silent });
        const authorMember = thread.channel?.channel_member_ids.find((member) =>
            member.persona?.eq(message.author)
        );
        if (authorMember) {
            authorMember.seen_message_id = message;
        }
    }
}

export const discussCoreCommon = {
    dependencies: [
        "bus_service",
        "mail.out_of_focus",
        "mail.store",
        "notification",
        "orm",
        "presence",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        const discussCoreCommon = reactive(new DiscussCoreCommon(env, services));
        discussCoreCommon.setup(env, services);
        return discussCoreCommon;
    },
};

registry.category("services").add("discuss.core.common", discussCoreCommon);
