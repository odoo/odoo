/* @odoo-module */

import { removeAttachment } from "@mail/core/common/attachment_service";
import { CannedResponse } from "@mail/core/common/canned_response_model";
import { LinkPreview } from "@mail/core/common/link_preview_model";
import {
    createTransientMessage,
    insertMessage,
    updateStarred,
} from "@mail/core/common/message_service";
import { insertPersona } from "@mail/core/common/persona_service";
import {
    createChannelThread,
    fetchMoreMessages,
    insertThread,
    markThreadAsFetched,
    markThreadAsRead,
    pinThread,
    removeThread,
    sortChannels,
    updateThread,
    updateThreadSeen,
} from "@mail/core/common/thread_service";
import { removeFromArray, removeFromArrayWithPredicate } from "@mail/utils/common/arrays";
import { cleanTerm } from "@mail/utils/common/format";
import { createLocalId } from "@mail/utils/common/misc";
import { makeFnPatchable } from "@mail/utils/common/patch";

import { markup, reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";

let actionService;
let imStatusService;
let notificationService;
/** @type {import("@mail/core/common/out_of_focus_service").OutOfFocusService} */
let outOfFocusService;
let orm;
let presence;
let registeredImStatusPartners;
let router;
let rpc;
/** @type {import("@mail/core/common/store_service").Store} */
let store;
/** @type {import("@mail/core/common/user_settings_service").UserSettings} */
let userSettingsService;

function handleNotification(notifications) {
    const channelsLeft = new Set(
        notifications.reduce((channelIds, notification) => {
            if (notification.type === "discuss.channel/leave") {
                channelIds.push(notification.payload.id);
            }
            return channelIds;
        }, [])
    );
    for (const notif of notifications) {
        switch (notif.type) {
            case "mail.activity/updated":
                if (notif.payload.activity_created) {
                    store.activityCounter++;
                }
                if (notif.payload.activity_deleted) {
                    store.activityCounter--;
                }
                break;
            case "discuss.channel/new_message":
                if (channelsLeft.has(notif.payload.id)) {
                    // Do not handle new message notification if the channel
                    // was just left. This issue occurs because the
                    // "discuss.channel/leave" and the
                    // "discuss.channel/new_message" notifications come from
                    // the bus as a batch.
                    return;
                }
                _handleNotificationNewMessage(notif);
                break;
            case "discuss.channel/leave":
                {
                    const thread = insertThread({
                        ...notif.payload,
                        model: "discuss.channel",
                    });
                    removeThread(thread);
                    if (thread.localId === store.discuss.threadLocalId) {
                        store.discuss.threadLocalId = undefined;
                    }
                    notificationService.add(
                        sprintf(_t("You unsubscribed from %s."), thread.displayName),
                        { type: "info" }
                    );
                }
                break;
            case "mail.record/insert":
                _handleNotificationRecordInsert(notif);
                break;
            case "discuss.channel/joined": {
                const { channel, invited_by_user_id: invitedByUserId } = notif.payload;
                const thread = insertThread({
                    ...channel,
                    model: "discuss.channel",
                    channel: channel.channel,
                    type: channel.channel.channel_type,
                });
                if (invitedByUserId && invitedByUserId !== store.user?.user?.id) {
                    notificationService.add(
                        sprintf(_t("You have been invited to #%s"), thread.displayName),
                        { type: "info" }
                    );
                }
                break;
            }
            case "discuss.channel/legacy_insert":
                insertThread({
                    id: notif.payload.channel.id,
                    model: "discuss.channel",
                    type: notif.payload.channel.channel_type,
                    ...notif.payload,
                });
                break;
            case "discuss.channel/transient_message": {
                const channel =
                    store.threads[createLocalId("discuss.channel", notif.payload.res_id)];
                const message = createTransientMessage(
                    Object.assign(notif.payload, { body: markup(notif.payload.body) })
                );
                channel.messages.push(message);
                channel.transientMessages.push(message);
                break;
            }
            case "mail.link.preview/delete":
                {
                    const { id, message_id } = notif.payload;
                    removeFromArrayWithPredicate(
                        store.messages[message_id].linkPreviews,
                        (linkPreview) => linkPreview.id === id
                    );
                }
                break;
            case "mail.message/inbox": {
                const data = Object.assign(notif.payload, { body: markup(notif.payload.body) });
                const message = insertMessage(data);
                const inbox = store.discuss.inbox;
                if (!inbox.messages.includes(message)) {
                    inbox.messages.push(message);
                    inbox.counter++;
                }
                const thread = message.originThread;
                if (!thread.needactionMessages.includes(message)) {
                    thread.needactionMessages.push(message);
                    thread.message_needaction_counter++;
                }
                break;
            }
            case "mail.message/delete": {
                for (const messageId of notif.payload.message_ids) {
                    const message = store.messages[messageId];
                    if (!message) {
                        continue;
                    }
                    if (message.isNeedaction) {
                        removeFromArrayWithPredicate(
                            store.discuss.inbox.messages,
                            ({ id }) => id === message.id
                        );
                        store.discuss.inbox.counter--;
                    }
                    if (message.isStarred) {
                        removeFromArrayWithPredicate(
                            store.discuss.starred.messages,
                            ({ id }) => id === message.id
                        );
                        store.discuss.starred.counter--;
                    }
                    delete store.messages[messageId];
                    if (message.originThread) {
                        removeFromArrayWithPredicate(
                            message.originThread.messages,
                            ({ id }) => id === message.id
                        );
                        if (message.isNeedaction) {
                            removeFromArrayWithPredicate(
                                message.originThread.needactionMessages,
                                ({ id }) => id === message.id
                            );
                        }
                        if (message.id > message.originThread.seen_message_id) {
                            message.originThread.message_unread_counter--;
                        }
                    }
                }
                break;
            }
            case "mail.message/mark_as_read": {
                const { message_ids: messageIds, needaction_inbox_counter } = notif.payload;
                const inbox = store.discuss.inbox;
                for (const messageId of messageIds) {
                    // We need to ignore all not yet known messages because we don't want them
                    // to be shown partially as they would be linked directly to cache.
                    // Furthermore, server should not send back all messageIds marked as read
                    // but something like last read messageId or something like that.
                    // (just imagine you mark 1000 messages as read ... )
                    const message = store.messages[messageId];
                    if (!message) {
                        continue;
                    }
                    // update thread counter (before removing message from Inbox, to ensure isNeedaction check is correct)
                    const originThread = message.originThread;
                    if (originThread && message.isNeedaction) {
                        originThread.message_needaction_counter--;
                        removeFromArrayWithPredicate(
                            originThread.needactionMessages,
                            ({ id }) => id === messageId
                        );
                    }
                    // move messages from Inbox to history
                    const partnerIndex = message.needaction_partner_ids.find(
                        (p) => p === store.user?.id
                    );
                    removeFromArray(message.needaction_partner_ids, partnerIndex);
                    removeFromArrayWithPredicate(inbox.messages, ({ id }) => id === messageId);
                    const history = store.discuss.history;
                    if (!history.messages.includes(message)) {
                        history.messages.push(message);
                    }
                }
                inbox.counter = needaction_inbox_counter;
                if (inbox.counter > inbox.messages.length) {
                    fetchMoreMessages(inbox);
                }
                break;
            }
            case "mail.message/toggle_star": {
                const { message_ids: messageIds, starred } = notif.payload;
                for (const messageId of messageIds) {
                    const message = insertMessage({ id: messageId });
                    updateStarred(message, starred);
                }
                break;
            }
            case "discuss.channel.member/seen": {
                const { channel_id, last_message_id, partner_id } = notif.payload;
                const channel = store.threads[createLocalId("discuss.channel", channel_id)];
                if (!channel) {
                    // for example seen from another browser, the current one has no
                    // knowledge of the channel
                    continue;
                }
                if (partner_id && partner_id === store.user?.id) {
                    updateThreadSeen(channel, last_message_id);
                }
                const seenInfo = channel.seenInfos.find(
                    (seenInfo) => seenInfo.partner.id === partner_id
                );
                if (seenInfo) {
                    seenInfo.lastSeenMessage = { id: last_message_id };
                }
                break;
            }

            case "discuss.channel.member/fetched": {
                const { channel_id, last_message_id, partner_id } = notif.payload;
                const channel = store.threads[createLocalId("discuss.channel", channel_id)];
                if (!channel) {
                    return;
                }
                const seenInfo = channel.seenInfos.find(
                    (seenInfo) => seenInfo.partner.id === partner_id
                );
                if (seenInfo) {
                    seenInfo.lastFetchedMessage = { id: last_message_id };
                }
                break;
            }
            case "discuss.channel/unpin": {
                const thread = store.threads[createLocalId("discuss.channel", notif.payload.id)];
                if (!thread) {
                    return;
                }
                thread.is_pinned = false;
                notificationService.add(
                    sprintf(_t("You unpinned your conversation with %s"), thread.displayName),
                    { type: "info" }
                );
                break;
            }
            case "mail.message/notification_update":
                {
                    notif.payload.elements.map((message) => {
                        insertMessage({
                            ...message,
                            body: markup(message.body),
                            // implicit: failures are sent by the server at
                            // initialization only if the current partner is
                            // author of the message
                            author: store.self,
                        });
                    });
                }
                break;
            case "discuss.channel/last_interest_dt_changed":
                _handleNotificationLastInterestDtChanged(notif);
                break;
            case "ir.attachment/delete":
                {
                    const { id: attachmentId, message: messageData } = notif.payload;
                    if (messageData) {
                        insertMessage({ ...messageData });
                    }
                    const attachment = store.attachments[attachmentId];
                    if (!attachment) {
                        return;
                    }
                    removeAttachment(attachment);
                }
                break;
        }
    }
}

/**
 * Import data received from init_messaging
 */
export const initializeMessaging = makeFnPatchable(function () {
    rpc("/mail/init_messaging", {}, { silent: true }).then(initMessagingCallback);
});

export const initMessagingCallback = makeFnPatchable(function (data) {
    if (data.current_partner) {
        store.user = insertPersona({
            ...data.current_partner,
            type: "partner",
        });
    }
    if (data.currentGuest) {
        store.guest = insertPersona({
            ...data.currentGuest,
            type: "guest",
            channelId: data.channels[0]?.id,
        });
    }
    store.odoobot = insertPersona({
        ...data.odoobot,
        type: "partner",
    });
    for (const channelData of data.channels) {
        createChannelThread(channelData);
    }
    sortChannels();
    const settings = data.current_user_settings;
    userSettingsService.updateFromCommands(settings);
    userSettingsService.id = settings.id;
    store.companyName = data.companyName;
    store.discuss.channels.isOpen = settings.is_discuss_sidebar_category_channel_open;
    store.discuss.chats.isOpen = settings.is_discuss_sidebar_category_chat_open;
    store.discuss.inbox.counter = data.needaction_inbox_counter;
    store.internalUserGroupId = data.internalUserGroupId;
    store.discuss.starred.counter = data.starred_counter;
    store.discuss.isActive =
        data.menu_id === router.current.hash?.menu_id ||
        router.hash?.action === "mail.action_discuss";
    (data.shortcodes ?? []).forEach((code) => {
        insertCannedResponse(code);
    });
    store.hasLinkPreviewFeature = data.hasLinkPreviewFeature;
    store.initBusId = data.initBusId;
    store.messagingReadyProm.resolve();
    store.isMessagingReady = true;
});

function insertCannedResponse(data) {
    let cannedResponse = store.cannedResponses[data.id];
    if (!cannedResponse) {
        store.cannedResponses[data.id] = new CannedResponse();
        cannedResponse = store.cannedResponses[data.id];
    }
    Object.assign(cannedResponse, {
        id: data.id,
        name: data.source,
        substitution: data.substitution,
    });
    return cannedResponse;
}

export function loadFailures() {
    rpc("/mail/load_message_failures", {}, { silent: true }).then((messages) => {
        messages.map((messageData) =>
            insertMessage({
                ...messageData,
                body: messageData.body ? markup(messageData.body) : messageData.body,
                // implicit: failures are sent by the server at
                // initialization only if the current partner is
                // author of the message
                author: store.user,
            })
        );
        store.notificationGroups.sort((n1, n2) => n2.lastMessage.id - n1.lastMessage.id);
    });
}

export function openDocument({ id, model }) {
    actionService.doAction({
        type: "ir.actions.act_window",
        res_model: model,
        views: [[false, "form"]],
        res_id: id,
    });
}

export async function searchPartners(searchStr = "", limit = 10) {
    let partners = [];
    const searchTerm = cleanTerm(searchStr);
    for (const localId in store.personas) {
        const persona = store.personas[localId];
        if (persona.type !== "partner") {
            continue;
        }
        const partner = persona;
        // todo: need to filter out non-user partners (there was a user key)
        // also, filter out inactive partners
        if (partner.name && cleanTerm(partner.name).includes(searchTerm)) {
            partners.push(partner);
            if (partners.length >= limit) {
                break;
            }
        }
    }
    if (!partners.length) {
        const partnersData = await orm.silent.call("res.partner", "im_search", [searchTerm, limit]);
        partners = partnersData.map((data) => insertPersona({ ...data, type: "partner" }));
    }
    return partners;
}

function updateImStatusRegistration() {
    imStatusService.registerToImStatus(
        "res.partner",
        /**
         * Read value from registeredImStatusPartners own reactive rather than
         * from store reactive to ensure the callback keeps being registered.
         */
        [...registeredImStatusPartners]
    );
}

export const _handleNotificationNewMessage = makeFnPatchable(async function (notif) {
    const { id, message: messageData } = notif.payload;
    let channel = store.threads[createLocalId("discuss.channel", id)];
    if (!channel || !channel.type) {
        const [channelData] = await orm.call("discuss.channel", "channel_info", [id]);
        channel = insertThread({
            model: "discuss.channel",
            type: channelData.channel.channel_type,
            ...channelData,
        });
    }
    if (!channel.is_pinned) {
        pinThread(channel);
    }
    removeFromArrayWithPredicate(channel.messages, ({ id }) => id === messageData.temporary_id);
    delete store.messages[messageData.temporary_id];
    messageData.temporary_id = null;
    if ("parentMessage" in messageData && messageData.parentMessage.body) {
        messageData.parentMessage.body = markup(messageData.parentMessage.body);
    }
    const data = Object.assign(messageData, {
        body: markup(messageData.body),
    });
    const message = insertMessage({
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
            if (notif.id > store.initBusId) {
                channel.message_unread_counter++;
            }
            if (message.isNeedaction) {
                const inbox = store.discuss.inbox;
                if (!inbox.messages.includes(message)) {
                    inbox.messages.push(message);
                    if (notif.id > store.initBusId) {
                        inbox.counter++;
                    }
                }
                if (!channel.needactionMessages.includes(message)) {
                    channel.needactionMessages.push(message);
                    if (notif.id > store.initBusId) {
                        channel.message_needaction_counter++;
                    }
                }
            }
        }
    }
    if (channel.chatPartnerId !== store.odoobot?.id) {
        if (!presence.isOdooFocused() && channel.isChatChannel) {
            outOfFocusService.notify(message, channel);
        }

        if (channel.type !== "channel" && !store.guest) {
            // disabled on non-channel threads and
            // on "channel" channels for performance reasons
            markThreadAsFetched(channel);
        }
    }
    if (
        !channel.loadNewer &&
        !message.isSelfAuthored &&
        channel.composer.isFocused &&
        channel.newestPersistentMessage &&
        !store.guest &&
        channel.newestPersistentMessage === channel.newestMessage
    ) {
        markThreadAsRead(channel);
    }
});

export const _handleNotificationLastInterestDtChanged = makeFnPatchable(function (notif) {
    const { id, last_interest_dt } = notif.payload;
    const channel = store.threads[createLocalId("discuss.channel", id)];
    if (channel) {
        updateThread(channel, { last_interest_dt });
    }
    if (["chat", "group"].includes(channel?.type)) {
        sortChannels();
    }
});

export const _handleNotificationRecordInsert = makeFnPatchable(function (notif) {
    if (notif.payload.Thread) {
        insertThread(notif.payload.Thread);
    }
    if (notif.payload.Channel) {
        insertThread({
            id: notif.payload.Channel.id,
            model: "discuss.channel",
            channel: notif.payload.Channel,
        });
    }
    if (notif.payload.Partner) {
        const partners = Array.isArray(notif.payload.Partner)
            ? notif.payload.Partner
            : [notif.payload.Partner];
        for (const partner of partners) {
            if (partner.im_status) {
                insertPersona({ ...partner, type: "partner" });
            }
        }
    }
    if (notif.payload.Guest) {
        const guests = Array.isArray(notif.payload.Guest)
            ? notif.payload.Guest
            : [notif.payload.Guest];
        for (const guest of guests) {
            insertPersona({ ...guest, type: "guest" });
        }
    }
    const { LinkPreview: linkPreviews } = notif.payload;
    if (linkPreviews) {
        for (const linkPreview of linkPreviews) {
            store.messages[linkPreview.message.id]?.linkPreviews.push(new LinkPreview(linkPreview));
        }
    }
    const { Message: messageData } = notif.payload;
    if (messageData) {
        const isStarred = store.messages[messageData.id]?.isStarred;
        const message = insertMessage({
            ...messageData,
            body: messageData.body ? markup(messageData.body) : messageData.body,
        });
        if (isStarred && message.isEmpty) {
            updateStarred(message, false);
        }
    }
    const { "res.users.settings": settings } = notif.payload;
    if (settings) {
        userSettingsService.updateFromCommands(settings);
        store.discuss.chats.isOpen =
            settings.is_discuss_sidebar_category_chat_open ?? store.discuss.chats.isOpen;
        store.discuss.channels.isOpen =
            settings.is_discuss_sidebar_category_channel_open ?? store.discuss.channels.isOpen;
    }
    const { "res.users.settings.volumes": volumeSettings } = notif.payload;
    if (volumeSettings) {
        userSettingsService.setVolumes(volumeSettings);
    }
});

/**
 * @typedef {Messaging} Messaging
 */
export class Messaging {
    constructor(...args) {
        this.setup(...args);
    }

    setup(env, services) {
        this.env = env;
        actionService = services.action;
        store = services["mail.store"];
        rpc = this.rpc = services.rpc;
        orm = this.orm = services.orm;
        notificationService = services.notification;
        userSettingsService = services["mail.user_settings"];
        outOfFocusService = services["mail.out_of_focus"];
        router = services.router;
        this.bus = services.bus_service;
        presence = services.presence;
        imStatusService = services.im_status;
        const user = services.user;
        insertPersona({ id: user.partnerId, type: "partner", isAdmin: user.isAdmin });
        registeredImStatusPartners = reactive([], () => updateImStatusRegistration());
        store.registeredImStatusPartners = registeredImStatusPartners;
        store.discuss.inbox = insertThread({
            id: "inbox",
            model: "mail.box",
            name: _t("Inbox"),
            type: "mailbox",
        });
        store.discuss.starred = insertThread({
            id: "starred",
            model: "mail.box",
            name: _t("Starred"),
            type: "mailbox",
            counter: 0,
        });
        store.discuss.history = insertThread({
            id: "history",
            model: "mail.box",
            name: _t("History"),
            type: "mailbox",
            counter: 0,
        });
        updateImStatusRegistration();
    }
}

export const messagingService = {
    dependencies: [
        "action",
        "mail.store",
        "discuss.channel.member",
        "rpc",
        "orm",
        "user",
        "router",
        "bus_service",
        "im_status",
        "notification",
        "presence",
        "mail.attachment",
        "mail.user_settings",
        "mail.message",
        "mail.thread",
        "mail.persona",
        "mail.out_of_focus",
    ],
    start(env, services) {
        // compute initial discuss thread if not on public page
        if (!services["mail.store"].inPublicPage) {
            const activeId = services.router.current.hash.active_id ?? "mail.box_inbox";
            let [model, id] =
                typeof activeId === "number" ? ["discuss.channel", activeId] : activeId.split("_");
            if (model === "mail.channel") {
                // legacy format (sent in old emails, shared links, ...)
                model = "discuss.channel";
            }
            services["mail.store"].discuss.threadLocalId = createLocalId(model, id);
        }
        const messaging = new Messaging(env, services);
        initializeMessaging();
        services["mail.store"].messagingReadyProm.then(() => {
            services.bus_service.addEventListener("notification", (notifEvent) => {
                handleNotification(notifEvent.detail);
            });
            services.bus_service.start();
        });
        return messaging;
    },
};

registry.category("services").add("mail.messaging", messagingService);
