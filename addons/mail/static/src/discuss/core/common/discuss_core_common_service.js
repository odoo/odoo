import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
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
        this.busService.addEventListener(
            "connect",
            () =>
                this.store.imStatusTrackedPersonas.forEach((p) => {
                    const model = p.type === "partner" ? "res.partner" : "mail.guest";
                    this.busService.addChannel(`odoo-presence-${model}_${p.id}`);
                }),
            { once: true }
        );
        this.busService.subscribe("discuss.channel/leave", (payload) => {
            const { Thread } = this.store.insert(payload);
            const [thread] = Thread;
            if (thread.notifyOnLeave) {
                this.notificationService.add(
                    _t("You left %(channel)s.", { channel: thread.displayName }),
                    { type: "info" }
                );
            }
            thread.closeChatWindow();
        });
        this.busService.subscribe("discuss.channel/delete", (payload, metadata) => {
            const thread = this.store.Thread.insert({
                id: payload.id,
                model: "discuss.channel",
            });
            this._handleNotificationChannelDelete(thread, metadata);
        });
        this.busService.subscribe("discuss.channel/new_message", (payload, metadata) =>
            this._handleNotificationNewMessage(payload, metadata)
        );
        this.busService.subscribe("discuss.channel/transient_message", (payload) => {
            const { body, channel_id } = payload;
            const lastMessageId = this.store.getLastMessageId();
            const message = this.store["mail.message"].insert(
                {
                    author: this.store.odoobot,
                    body,
                    id: lastMessageId + 0.01,
                    is_note: true,
                    is_transient: true,
                    thread: { id: channel_id, model: "discuss.channel" },
                },
                { html: true }
            );
            message.thread.messages.push(message);
            message.thread.transientMessages.push(message);
        });
        this.busService.subscribe("discuss.channel/unpin", (payload) => {
            const thread = this.store.Thread.get({ model: "discuss.channel", id: payload.id });
            if (thread) {
                thread.is_pinned = false;
                thread.closeChatWindow();
            }
        });
        this.busService.subscribe("discuss.channel.member/fetched", (payload) => {
            const { channel_id, id, last_message_id, partner_id } = payload;
            this.store["discuss.channel.member"].insert({
                id,
                fetched_message_id: { id: last_message_id },
                persona: { type: "partner", id: partner_id },
                thread: { id: channel_id, model: "discuss.channel" },
            });
        });
        this.env.bus.addEventListener("mail.message/delete", ({ detail: { message, notifId } }) => {
            if (message.thread) {
                const { selfMember } = message.thread;
                if (
                    message.id > selfMember?.seen_message_id.id &&
                    notifId > selfMember.message_unread_counter_bus_id
                ) {
                    selfMember.message_unread_counter--;
                }
            }
        });
    }

    /**
     * @param {import("models").Thread} thread
     * @param {{ notifId: number}} metadata
     */
    _handleNotificationChannelDelete(thread, metadata) {
        thread.closeChatWindow();
        thread.messages.splice(0, thread.messages.length);
        thread.delete();
    }

    async _handleNotificationNewMessage(payload, { id: notifId }) {
        const { data, id: channelId, silent, temporary_id } = payload;
        const channel = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: channelId,
        });
        if (!channel) {
            return;
        }
        const { "mail.message": messages = [] } = this.store.insert(data, { html: true });
        /** @type {import("models").Message} */
        const message = messages[0];
        if (message.notIn(channel.messages)) {
            if (!channel.loadNewer) {
                channel.addOrReplaceMessage(message, this.store["mail.message"].get(temporary_id));
            } else if (channel.status === "loading") {
                channel.pendingNewMessages.push(message);
            }
            if (message.isSelfAuthored) {
                channel.onNewSelfMessage(message);
            } else {
                if (!channel.isDisplayed && channel.selfMember) {
                    channel.selfMember.syncUnread = true;
                    channel.scrollUnread = true;
                }
                if (notifId > channel.selfMember?.message_unread_counter_bus_id) {
                    channel.selfMember.message_unread_counter++;
                }
            }
        }
        if (
            channel.channel_type !== "channel" &&
            this.store.self.type === "partner" &&
            channel.selfMember
        ) {
            // disabled on non-channel threads and
            // on "channel" channels for performance reasons
            channel.markAsFetched();
        }
        if (
            !channel.loadNewer &&
            !message.isSelfAuthored &&
            channel.composer.isFocused &&
            this.store.self.type === "partner" &&
            channel.newestPersistentMessage?.eq(channel.newestMessage)
        ) {
            channel.markAsRead({ sync: false });
        }
        this.env.bus.trigger("discuss.channel/new_message", { channel, message, silent });
        const authorMember = channel.channel_member_ids.find(({ persona }) =>
            persona?.eq(message.author)
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
