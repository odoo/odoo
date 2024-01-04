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
        this.messagingService.isReady.then((data) => {
            this.busService.subscribe("discuss.channel/joined", (payload) => {
                const { channel, invited_by_user_id: invitedByUserId } = payload;
                const thread = this.store.Thread.insert(channel);
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
            this.busService.subscribe("discuss.channel/transient_message", (payload) => {
                const { body, originThread } = payload;
                const channel = this.store.Thread.get(originThread);
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
                channel.messages.push(message);
                channel.transientMessages.push(message);
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
            this.busService.subscribe("discuss.channel.member/seen", (payload) => {
                const { channel_id, guest_id, id, last_message_id, partner_id } = payload;
                const member = this.store.ChannelMember.insert({
                    id,
                    seen_message_id: { id: last_message_id },
                    persona: { type: partner_id ? "partner" : "guest", id: partner_id ?? guest_id },
                    thread: { id: channel_id, model: "discuss.channel" },
                });
                if (member?.persona.eq(this.store.self)) {
                    this.threadService.updateSeen(member.thread, last_message_id);
                }
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
