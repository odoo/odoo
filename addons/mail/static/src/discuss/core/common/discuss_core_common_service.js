/* @odoo-module */

import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";

import { markup, reactive } from "@odoo/owl";

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
        this.rpc = services.rpc;
        this.messageService = services["mail.message"];
        this.messagingService = services["mail.messaging"];
        this.outOfFocusService = services["mail.out_of_focus"];
        this.store = services["mail.store"];
        this.threadService = services["mail.thread"];
    }

    setup() {
        this.messagingService.isReady.then((data) => {
            for (const channelData of data.channels) {
                this.createChannelThread(channelData);
            }
            this.threadService.sortChannels();
            this.busService.subscribe("discuss.channel/joined", (payload) => {
                const { channel, invited_by_user_id: invitedByUserId } = payload;
                const thread = this.store.Thread.insert({
                    ...channel,
                    model: "discuss.channel",
                    channel: channel.channel,
                    type: channel.channel.channel_type,
                });
                if (invitedByUserId && invitedByUserId !== this.store.user?.user?.id) {
                    this.notificationService.add(
                        _t("You have been invited to #%s", thread.displayName),
                        { type: "info" }
                    );
                }
            });
            this.busService.subscribe("discuss.channel/last_interest_dt_changed", (payload) => {
                const { id, last_interest_dt } = payload;
                const channel = this.store.Thread.get({ model: "discuss.channel", id });
                if (channel) {
                    this.threadService.update(channel, { last_interest_dt });
                    if (channel.type !== "channel") {
                        this.threadService.sortChannels();
                    }
                }
            });
            this.busService.subscribe("discuss.channel/leave", (payload) => {
                const thread = this.store.Thread.insert({
                    ...payload,
                    model: "discuss.channel",
                });
                this.threadService.remove(thread);
                if (thread.localId === this.store.discuss.threadLocalId) {
                    this.store.discuss.threadLocalId = undefined;
                }
                this.notificationService.add(_t("You unsubscribed from %s.", thread.displayName), {
                    type: "info",
                });
            });
            this.busService.subscribe("discuss.channel/legacy_insert", (payload) => {
                this.store.Thread.insert({
                    id: payload.channel.id,
                    model: "discuss.channel",
                    type: payload.channel.channel_type,
                    ...payload,
                });
            });
            this.busService.addEventListener("notification", ({ detail: notifications }) => {
                // Do not handle new message notification if the channel was just left. This issue
                // occurs because the "discuss.channel/leave" and the "discuss.channel/new_message"
                // notifications come from the bus as a batch.
                const channelsLeft = new Set(
                    notifications
                        .filter(({ type }) => type === "discuss.channel/leave")
                        .map(({ payload }) => payload.id)
                );
                for (const notif of notifications.filter(
                    ({ payload, type }) =>
                        type === "discuss.channel/new_message" && !channelsLeft.has(payload.id)
                )) {
                    this._handleNotificationNewMessage(notif);
                }
            });
            this.busService.subscribe("discuss.channel/transient_message", (payload) => {
                const channel = this.store.Thread.get({
                    model: "discuss.channel",
                    id: payload.res_id,
                });
                const message = this.messageService.createTransient(
                    Object.assign(payload, { body: markup(payload.body) })
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
                const { channel_id, last_message_id, partner_id } = payload;
                const channel = this.store.Thread.get({ model: "discuss.channel", id: channel_id });
                if (channel) {
                    const seenInfo = channel.seenInfos.find(
                        (seenInfo) => seenInfo.partner.id === partner_id
                    );
                    if (seenInfo) {
                        seenInfo.lastFetchedMessage = { id: last_message_id };
                    }
                }
            });
            this.busService.subscribe("discuss.channel.member/seen", (payload) => {
                const { channel_id, last_message_id, partner_id } = payload;
                const channel = this.store.Thread.get({ model: "discuss.channel", id: channel_id });
                if (!channel) {
                    // for example seen from another browser, the current one has no
                    // knowledge of the channel
                    return;
                }
                if (partner_id && partner_id === this.store.user?.id) {
                    this.threadService.updateSeen(channel, last_message_id);
                }
                const seenInfo = channel.seenInfos.find(
                    (seenInfo) => seenInfo.partner.id === partner_id
                );
                if (seenInfo) {
                    seenInfo.lastSeenMessage = { id: last_message_id };
                }
            });
            this.env.bus.addEventListener("mail.message/delete", ({ detail: { message } }) => {
                if (message.originThread) {
                    if (message.id > message.originThread.seen_message_id) {
                        message.originThread.message_unread_counter--;
                    }
                }
            });
            this.busService.subscribe("mail.record/insert", (payload) => {
                if (payload.Channel) {
                    this.store.Thread.insert({
                        id: payload.Channel.id,
                        model: "discuss.channel",
                        channel: payload.Channel,
                    });
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
            type: serverData.channel.channel_type,
            isAdmin:
                serverData.channel.channel_type !== "group" &&
                serverData.create_uid === this.store.user?.user?.id,
        });
        return thread;
    }

    async createGroupChat({ default_display_mode, partners_to }) {
        const data = await this.orm.call("discuss.channel", "create_group", [], {
            default_display_mode,
            partners_to,
        });
        const channel = this.createChannelThread(data);
        this.threadService.sortChannels();
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

    async _handleNotificationNewMessage(notif) {
        const { id, message: messageData } = notif.payload;
        let channel = this.store.Thread.get({ model: "discuss.channel", id });
        if (!channel || !channel.type) {
            const [channelData] = await this.rpc("/discuss/channel/info", { channel_id: id });
            channel = this.store.Thread.insert({
                model: "discuss.channel",
                type: channelData.channel.channel_type,
                ...channelData,
            });
        }
        if (!channel.is_pinned) {
            this.threadService.pin(channel);
        }
        removeFromArrayWithPredicate(channel.messages, ({ id }) => id === messageData.temporary_id);
        this.store.Message.get(messageData.temporary_id)?.delete();
        messageData.temporary_id = null;
        if ("parentMessage" in messageData && messageData.parentMessage.body) {
            messageData.parentMessage.body = markup(messageData.parentMessage.body);
        }
        const data = Object.assign(messageData, {
            body: markup(messageData.body),
        });
        const message = this.store.Message.insert({
            ...data,
            res_id: channel.id,
            model: channel.model,
        });
        if (message.notIn(channel.messages)) {
            if (!channel.loadNewer) {
                channel.messages.push(message);
            } else if (channel.state === "loading") {
                channel.pendingNewMessages.push(message);
            }
            if (message.isSelfAuthored) {
                channel.seen_message_id = message.id;
            } else {
                if (notif.id > this.store.initBusId) {
                    channel.message_unread_counter++;
                }
                if (message.isNeedaction) {
                    const inbox = this.store.discuss.inbox;
                    if (message.notIn(inbox.messages)) {
                        inbox.messages.push(message);
                        if (notif.id > this.store.initBusId) {
                            inbox.counter++;
                        }
                    }
                    if (message.notIn(channel.needactionMessages)) {
                        channel.needactionMessages.push(message);
                        if (notif.id > this.store.initBusId) {
                            channel.message_needaction_counter++;
                        }
                    }
                }
            }
        }
        if (!channel.chatPartner?.eq(this.store.odoobot)) {
            if (
                !this.presence.isOdooFocused() &&
                channel.isChatChannel &&
                !message.isSelfAuthored
            ) {
                this.outOfFocusService.notify(message, channel);
            }

            if (channel.type !== "channel" && !this.store.guest) {
                // disabled on non-channel threads and
                // on "channel" channels for performance reasons
                this.threadService.markAsFetched(channel);
            }
        }
        if (
            !channel.loadNewer &&
            !message.isSelfAuthored &&
            channel.composer.isFocused &&
            !this.store.guest &&
            channel.newestPersistentMessage?.eq(channel.newestMessage)
        ) {
            this.threadService.markAsRead(channel);
        }
        this.env.bus.trigger("discuss.channel/new_message", { channel, message });
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
        "rpc",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const discussCoreCommon = reactive(new DiscussCoreCommon(env, services));
        discussCoreCommon.setup();
        return discussCoreCommon;
    },
};

registry.category("services").add("discuss.core.common", discussCoreCommon);
