/* @odoo-module */

import { reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class DiscussCoreCommon {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.busService = services.bus_service;
        this.env = env;
        this.notificationService = services.notification;
        this.orm = services.orm;
        this.presence = services.presence;
        this.messageService = services["mail.message"];
        this.messagingService = services["mail.messaging"];
        this.store = services["mail.store"];
        this.threadService = services["mail.thread"];
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
        this.messagingService.isReady.then(() => {
            this.busService.subscribe("discuss.channel/joined", async (payload) => {
                const { channel, invited_by_user_id: invitedByUserId } = payload;
                const thread = this.store.Thread.insert(channel);
                await thread.fetchChannelInfo();
                if (invitedByUserId && invitedByUserId !== this.store.self?.user?.id) {
                    this.notificationService.add(
                        _t("You have been invited to #%s", thread.displayName),
                        { type: "info" }
                    );
                }
            });
            this.busService.subscribe("discuss.channel/leave", (payload) => {
                const thread = this.store.Thread.insert(payload);
                this.notificationService.add(_t("You unsubscribed from %s.", thread.displayName), {
                    type: "info",
                });
                thread.delete();
            });
            this.busService.subscribe("discuss.channel/delete", (payload) => {
                const thread = this.store.Thread.insert({
                    id: payload.id,
                    model: "discuss.channel",
                });
                const filteredStarredMessages = [];
                let starredCounter = 0;
                for (const msg of this.store.discuss.starred.messages) {
                    if (!msg.originThread?.eq(thread)) {
                        filteredStarredMessages.push(msg);
                    } else {
                        starredCounter++;
                    }
                }
                this.store.discuss.starred.messages = filteredStarredMessages;
                this.store.discuss.starred.counter -= starredCounter;
                this.store.discuss.inbox.messages = this.store.discuss.inbox.messages.filter(
                    (msg) => !msg.originThread?.eq(thread)
                );
                this.store.discuss.inbox.counter -= thread.message_needaction_counter;
                this.store.discuss.history.messages = this.store.discuss.history.messages.filter(
                    (msg) => !msg.originThread?.eq(thread)
                );
                this.threadService.closeChatWindow?.(thread);
                if (thread.eq(this.store.discuss.thread)) {
                    this.threadService.setDiscussThread(this.store.discuss.inbox);
                }
                thread.messages.splice(0, thread.messages.length);
                thread.delete();
            });
            this.busService.subscribe("discuss.channel/new_message", (payload, metadata) =>
                this._handleNotificationNewMessage(payload, metadata)
            );
            this.busService.subscribe("discuss.channel/transient_message", (payload) => {
                const { body, originThread } = payload;
                const lastMessageId = this.messageService.getLastMessageId();
                const message = this.store.Message.insert(
                    {
                        author: this.store.odoobot,
                        body,
                        id: lastMessageId + 0.01,
                        is_note: true,
                        is_transient: true,
                        originThread,
                    },
                    { html: true }
                );
                message.originThread.messages.push(message);
                message.originThread.transientMessages.push(message);
            });
            this.busService.subscribe("discuss.channel/unpin", (payload) => {
                const thread = this.store.Thread.get({ model: "discuss.channel", id: payload.id });
                if (thread) {
                    thread.is_pinned = false;
                    this.notificationService.add(
                        _t("You unpinned your conversation with %s", thread.displayName),
                        { type: "info" }
                    );
                }
            });
            this.busService.subscribe("discuss.channel.member/fetched", (payload) => {
                const { channel_id, id, last_message_id, partner_id } = payload;
                this.store.ChannelMember.insert({
                    id,
                    fetched_message_id: { id: last_message_id },
                    persona: { type: "partner", id: partner_id },
                    thread: { id: channel_id, model: "discuss.channel" },
                });
            });
            this.env.bus.addEventListener("mail.message/delete", ({ detail: { message } }) => {
                if (message.originThread) {
                    if (message.id > message.originThread.seen_message_id) {
                        message.originThread.message_unread_counter--;
                    }
                }
            });
        });
    }

    /**
     * todo: merge this with store.Thread.insert() (?)
     *
     * @returns {Thread}
     */
    createChannelThread(serverData) {
        const thread = this.store.Thread.insert({
            ...serverData,
            model: "discuss.channel",
            type: serverData.channel_type,
            isAdmin:
                serverData.channel_type !== "group" &&
                serverData.create_uid === this.store.self?.user?.id,
        });
        return thread;
    }

    async createGroupChat({ default_display_mode, partners_to }) {
        const data = await this.orm.call("discuss.channel", "create_group", [], {
            default_display_mode,
            partners_to,
        });
        const channel = this.createChannelThread(data);
        this.threadService.open(channel);
        return channel;
    }

    /**
     * @param {[number]} partnerIds
     * @param {boolean} inChatWindow
     */
    async startChat(partnerIds, inChatWindow) {
        const partners_to = [...new Set([this.store.self.id, ...partnerIds])];
        if (partners_to.length === 1) {
            const chat = await this.threadService.joinChat(partners_to[0]);
            this.threadService.open(chat, inChatWindow);
        } else if (partners_to.length === 2) {
            const correspondentId = partners_to.find(
                (partnerId) => partnerId !== this.store.self.id
            );
            const chat = await this.threadService.joinChat(correspondentId);
            this.threadService.open(chat, inChatWindow);
        } else {
            await this.createGroupChat({ partners_to });
        }
    }

    async _handleNotificationNewMessage(payload, { id: notifId }) {
        const { id: channelId, message: messageData } = payload;
        const channel = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: channelId,
        });
        if (!channel) {
            return;
        }
        this.store.Message.get(messageData.temporary_id)?.delete();
        messageData.temporary_id = null;
        const message = this.store.Message.insert(messageData, { html: true });
        if (message.notIn(channel.messages)) {
            if (!channel.loadNewer) {
                channel.messages.push(message);
            } else if (channel.status === "loading") {
                channel.pendingNewMessages.push(message);
            }
            if (message.isSelfAuthored) {
                channel.seen_message_id = message.id;
            } else {
                if (notifId > channel.message_unread_counter_bus_id) {
                    channel.incrementUnreadCounter();
                }
            }
        }
        if (
            !channel.correspondent?.eq(this.store.odoobot) &&
            channel.channel_type !== "channel" &&
            this.store.self?.type === "partner"
        ) {
            // disabled on non-channel threads and
            // on "channel" channels for performance reasons
            this.threadService.markAsFetched(channel);
        }
        if (
            !channel.loadNewer &&
            !message.isSelfAuthored &&
            channel.composer.isFocused &&
            this.store.self?.type === "partner" &&
            channel.newestPersistentMessage?.eq(channel.newestMessage)
        ) {
            this.threadService.markAsRead(channel);
        }
        this.env.bus.trigger("discuss.channel/new_message", { channel, message });
        const authorMember = channel.channelMembers.find(({ persona }) =>
            persona?.eq(message.author)
        );
        if (authorMember) {
            authorMember.seen_message_id = message;
        }
        if (authorMember?.eq(channel.selfMember)) {
            this.threadService.updateSeen(authorMember.thread, message.id);
        }
    }
}

export const discussCoreCommon = {
    dependencies: [
        "bus_service",
        "mail.message",
        "mail.messaging",
        "mail.out_of_focus",
        "mail.store",
        "mail.thread",
        "notification",
        "orm",
        "presence",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const discussCoreCommon = reactive(new DiscussCoreCommon(env, services));
        discussCoreCommon.setup(env, services);
        return discussCoreCommon;
    },
};

registry.category("services").add("discuss.core.common", discussCoreCommon);
