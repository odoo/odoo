/* @odoo-module */

import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";
import { createLocalId } from "@mail/utils/common/misc";

import { markup, reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";

export class DiscussCoreCommon {
    constructor(env, services) {
        Object.assign(this, {
            busService: services.bus_service,
            env,
            presence: services.presence,
            rpc: services.rpc,
        });
        /** @type {import("@mail/core/common/message_service").MessageService} */
        this.messageService = services["mail.message"];
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        this.messagingService = services["mail.messaging"];
        this.notificationService = services.notification;
        /** @type {import("@mail/core/common/out_of_focus_service").OutOfFocusService} */
        this.outOfFocusService = services["mail.out_of_focus"];
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = services["mail.thread"];
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
    }

    setup() {
        this.messagingService.isReady.then(() => {
            this.busService.subscribe("discuss.channel/joined", (payload) => {
                const { channel, invited_by_user_id: invitedByUserId } = payload;
                const thread = this.threadService.insert({
                    ...channel,
                    model: "discuss.channel",
                    channel: channel.channel,
                    type: channel.channel.channel_type,
                });
                if (invitedByUserId && invitedByUserId !== this.store.user?.user?.id) {
                    this.notificationService.add(
                        sprintf(_t("You have been invited to #%s"), thread.displayName),
                        { type: "info" }
                    );
                }
            });
            this.busService.subscribe("discuss.channel/last_interest_dt_changed", (payload) => {
                const { id, last_interest_dt } = payload;
                const channel = this.store.threads[createLocalId("discuss.channel", id)];
                if (channel) {
                    this.threadService.update(channel, { last_interest_dt });
                    if (channel.type !== "channel") {
                        this.threadService.sortChannels();
                    }
                }
            });
            this.busService.subscribe("discuss.channel/leave", (payload) => {
                const thread = this.threadService.insert({
                    ...payload,
                    model: "discuss.channel",
                });
                this.threadService.remove(thread);
                if (thread.localId === this.store.discuss.threadLocalId) {
                    this.store.discuss.threadLocalId = undefined;
                }
                this.notificationService.add(
                    sprintf(_t("You unsubscribed from %s."), thread.displayName),
                    { type: "info" }
                );
            });
            this.busService.subscribe("discuss.channel/legacy_insert", (payload) => {
                this.threadService.insert({
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
                const channel =
                    this.store.threads[createLocalId("discuss.channel", payload.res_id)];
                const message = this.messageService.createTransient(
                    Object.assign(payload, { body: markup(payload.body) })
                );
                channel.messages.push(message);
                channel.transientMessages.push(message);
            });
            this.busService.subscribe("discuss.channel/unpin", (payload) => {
                const thread = this.store.threads[createLocalId("discuss.channel", payload.id)];
                if (thread) {
                    thread.is_pinned = false;
                    this.notificationService.add(
                        sprintf(_t("You unpinned your conversation with %s"), thread.displayName),
                        { type: "info" }
                    );
                }
            });
            this.busService.subscribe("discuss.channel.member/fetched", (payload) => {
                const { channel_id, last_message_id, partner_id } = payload;
                const channel = this.store.threads[createLocalId("discuss.channel", channel_id)];
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
                const channel = this.store.threads[createLocalId("discuss.channel", channel_id)];
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
            this.busService.start();
        });
    }

    async _handleNotificationNewMessage(notif) {
        const { id, message: messageData } = notif.payload;
        let channel = this.store.threads[createLocalId("discuss.channel", id)];
        if (!channel || !channel.type) {
            const [channelData] = await this.rpc("/discuss/channel/info", { channel_id: id });
            channel = this.threadService.insert({
                model: "discuss.channel",
                type: channelData.channel.channel_type,
                ...channelData,
            });
        }
        if (!channel.is_pinned) {
            this.threadService.pin(channel);
        }
        removeFromArrayWithPredicate(channel.messages, ({ id }) => id === messageData.temporary_id);
        delete this.store.messages[messageData.temporary_id];
        messageData.temporary_id = null;
        if ("parentMessage" in messageData && messageData.parentMessage.body) {
            messageData.parentMessage.body = markup(messageData.parentMessage.body);
        }
        const data = Object.assign(messageData, {
            body: markup(messageData.body),
        });
        const message = this.messageService.insert({
            ...data,
            res_id: channel.id,
            model: channel.model,
        });
        if (!channel.messages.includes(message)) {
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
                    if (!inbox.messages.includes(message)) {
                        inbox.messages.push(message);
                        if (notif.id > this.store.initBusId) {
                            inbox.counter++;
                        }
                    }
                    if (!channel.needactionMessages.includes(message)) {
                        channel.needactionMessages.push(message);
                        if (notif.id > this.store.initBusId) {
                            channel.message_needaction_counter++;
                        }
                    }
                }
            }
        }
        if (channel.chatPartnerId !== this.store.odoobot?.id) {
            if (!this.presence.isOdooFocused() && channel.isChatChannel) {
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
            channel.newestPersistentMessage &&
            !this.store.guest &&
            channel.newestPersistentMessage === channel.newestMessage
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
        "presence",
        "rpc",
    ],
    start(env, services) {
        const discussCoreCommon = reactive(new DiscussCoreCommon(env, services));
        discussCoreCommon.setup();
        return discussCoreCommon;
    },
};

registry.category("services").add("discuss.core.common", discussCoreCommon);
