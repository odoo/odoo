/* @odoo-module */

import { markup, reactive } from "@odoo/owl";
import { Deferred } from "@web/core/utils/concurrency";
import { memoize } from "@web/core/utils/functions";
import { cleanTerm, htmlToTextContentInline } from "@mail/new/utils/format";
import { removeFromArray, removeFromArrayWithPredicate } from "@mail/new/utils/arrays";
import { LinkPreview } from "./link_preview_model";
import { CannedResponse } from "./canned_response_model";
import { browser } from "@web/core/browser/browser";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { url } from "@web/core/utils/urls";
import { createLocalId } from "../utils/misc";
import { registry } from "@web/core/registry";

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers
export const OTHER_LONG_TYPING = 60000;

export const asyncMethods = [
    "fetchPreviews",
    "postMessage",
    "scheduleActivity",
    "updateMessage",
    "createChannel",
    "getChat",
    "joinChannel",
    "joinChat",
    "leaveChannel",
    "openChat",
    "toggleStar",
    "deleteMessage",
    "unstarAll",
    "notifyThreadNameToServer",
];

/**
 * @typedef {Messaging} Messaging
 */
export class Messaging {
    constructor(...args) {
        this.setup(...args);
    }

    setup(env, services, initialThreadLocalId) {
        this.env = env;
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = services["mail.store"];
        this.rpc = services.rpc;
        this.orm = services.orm;
        this.notificationService = services.notification;
        /** @type {import("@mail/new/core/sound_effects_service").SoundEffects} */
        this.soundEffectsService = services["mail.sound_effects"];
        /** @type {import("@mail/new/core/user_settings_service").UserSettings} */
        this.userSettingsService = services["mail.user_settings"];
        /** @type {import("@mail/new/core/thread_service").ThreadService} */
        this.threadService = services["mail.thread"];
        /** @type {import("@mail/new/core/message_service").MessageService} */
        this.messageService = services["mail.message"];
        /** @type {import("@mail/new/core/persona_service").PersonaService} */
        this.personaService = services["mail.persona"];
        /** @type {import("@mail/new/rtc/rtc_service").Rtc} */
        this.rtc = services["mail.rtc"];
        this.router = services.router;
        this.bus = services.bus_service;
        this.multiTab = services.multi_tab;
        this.presence = services.presence;
        this.isReady = new Deferred();
        this.imStatusService = services.im_status;
        this.outOfFocusAudio = new Audio();
        this.outOfFocusAudio.src = this.outOfFocusAudio.canPlayType("audio/ogg; codecs=vorbis")
            ? url("/mail/static/src/audio/ting.ogg")
            : url("/mail/static/src/audio/ting.mp3");
        this.bus.addEventListener("window_focus", () => {
            this.store.outOfFocusUnreadMessageCounter = 0;
            this.bus.trigger("set_title_part", {
                part: "_chat",
            });
        });
        const user = services.user;
        this.personaService.insert({ id: user.partnerId, type: "partner", isAdmin: user.isAdmin });
        this.registeredImStatusPartners = reactive([], () => this.updateImStatusRegistration());
        this.store.registeredImStatusPartners = this.registeredImStatusPartners;
        this.store.discuss.threadLocalId = initialThreadLocalId;
        this.store.discuss.inbox = this.threadService.insert({
            id: "inbox",
            model: "mail.box",
            name: _t("Inbox"),
            type: "mailbox",
        });
        this.store.discuss.starred = this.threadService.insert({
            id: "starred",
            model: "mail.box",
            name: _t("Starred"),
            type: "mailbox",
            counter: 0,
        });
        this.store.discuss.history = this.threadService.insert({
            id: "history",
            model: "mail.box",
            name: _t("History"),
            type: "mailbox",
            counter: 0,
        });
        this.updateImStatusRegistration();
    }

    /**
     * Import data received from init_messaging
     */
    initialize() {
        this.rpc("/mail/init_messaging", {}, { silent: true }).then(
            this.initMessagingCallback.bind(this)
        );
    }

    initMessagingCallback(data) {
        if (data.current_partner) {
            this.store.user = this.personaService.insert({
                ...data.current_partner,
                type: "partner",
            });
        }
        if (data.currentGuest) {
            this.store.guest = this.personaService.insert({
                ...data.currentGuest,
                type: "guest",
                channelId: data.channels[0]?.id,
            });
        }
        this.store.partnerRoot = this.personaService.insert({
            ...data.partner_root,
            type: "partner",
        });
        for (const channelData of data.channels) {
            this.threadService.createChannelThread(channelData);
        }
        this.threadService.sortChannels();
        const settings = data.current_user_settings;
        this.userSettingsService.updateFromCommands(settings);
        this.userSettingsService.id = settings.id;
        this.store.companyName = data.companyName;
        this.store.discuss.channels.isOpen = settings.is_discuss_sidebar_category_channel_open;
        this.store.discuss.chats.isOpen = settings.is_discuss_sidebar_category_chat_open;
        this.store.discuss.inbox.counter = data.needaction_inbox_counter;
        this.store.internalUserGroupId = data.internalUserGroupId;
        this.store.discuss.starred.counter = data.starred_counter;
        (data.shortcodes ?? []).forEach((code) => {
            this.insertCannedResponse(code);
        });
        this.isReady.resolve();
    }

    loadFailures() {
        this.rpc("/mail/load_message_failures", {}, { silent: true }).then((messages) => {
            messages.map((messageData) =>
                this.messageService.insert({
                    ...messageData,
                    body: messageData.body ? markup(messageData.body) : messageData.body,
                    // implicit: failures are sent by the server at
                    // initialization only if the current partner is
                    // author of the message
                    author: this.store.user,
                })
            );
            this.store.notificationGroups.sort(
                (n1, n2) => (n2.lastMessage?.id ?? 0) - (n1.lastMessage?.id ?? 0)
            );
        });
    }

    updateImStatusRegistration() {
        this.imStatusService.registerToImStatus(
            "res.partner",
            /**
             * Read value from registeredImStatusPartners own reactive rather than
             * from store reactive to ensure the callback keeps being registered.
             */
            [...this.registeredImStatusPartners]
        );
    }

    // -------------------------------------------------------------------------
    // process notifications received by the bus
    // -------------------------------------------------------------------------

    notifyOutOfFocusMessage(message, channel) {
        const author = message.author;
        let notificationTitle;
        if (!author) {
            notificationTitle = _t("New message");
        } else {
            if (channel.channel_type === "channel") {
                notificationTitle = sprintf(_t("%(author name)s from %(channel name)s"), {
                    "author name": author.name,
                    "channel name": channel.displayName,
                });
            } else {
                notificationTitle = author.name;
            }
        }
        const notificationContent = escape(
            htmlToTextContentInline(message.body).substr(0, PREVIEW_MSG_MAX_SIZE)
        );
        this.sendNotification({
            message: notificationContent,
            title: notificationTitle,
            type: "info",
        });
        this.store.outOfFocusUnreadMessageCounter++;
        const titlePattern =
            this.store.outOfFocusUnreadMessageCounter === 1 ? _t("%s Message") : _t("%s Messages");
        this.bus.trigger("set_title_part", {
            part: "_chat",
            title: sprintf(titlePattern, this.store.outOfFocusUnreadMessageCounter),
        });
    }

    /**
     * Send a notification, preferably a native one. If native
     * notifications are disable or unavailable on the current
     * platform, fallback on the notification service.
     *
     * @param {Object} param0
     * @param {string} [param0.message] The body of the
     * notification.
     * @param {string} [param0.title] The title of the notification.
     * @param {string} [param0.type] The type to be passed to the no
     * service when native notifications can't be sent.
     */
    sendNotification({ message, title, type }) {
        if (!this.canSendNativeNotification) {
            this.sendOdooNotification(message, { title, type });
            return;
        }
        if (!this.multiTab.isOnMainTab()) {
            return;
        }
        try {
            this.sendNativeNotification(title, message);
        } catch (error) {
            // Notification without Serviceworker in Chrome Android doesn't works anymore
            // So we fallback to the notification service in this case
            // https://bugs.chromium.org/p/chromium/issues/detail?id=481856
            if (error.message.includes("ServiceWorkerRegistration")) {
                this.sendOdooNotification(message, { title, type });
            } else {
                throw error;
            }
        }
    }

    /**
     * @param {string} message
     * @param {Object} options
     */
    async sendOdooNotification(message, options) {
        this.notificationService.add(message, options);
        if (this.canPlayAudio && this.multiTab.isOnMainTab()) {
            try {
                await this.outOfFocusAudio.play();
            } catch {
                // Ignore errors due to the user not having interracted
                // with the page before playing the sound.
            }
        }
    }

    /**
     * @param {string} title
     * @param {string} message
     */
    sendNativeNotification(title, message) {
        const notification = new Notification(
            // The native Notification API works with plain text and not HTML
            // unescaping is safe because done only at the **last** step
            _.unescape(title),
            {
                body: _.unescape(message),
                icon: this.icon,
            }
        );
        notification.addEventListener("click", ({ target: notification }) => {
            window.focus();
            notification.close();
        });
    }

    get canPlayAudio() {
        return typeof Audio !== "undefined";
    }

    get canSendNativeNotification() {
        return Boolean(browser.Notification && browser.Notification.permission === "granted");
    }

    handleNotification(notifications) {
        console.log("notifications received", notifications);
        for (const notif of notifications) {
            switch (notif.type) {
                case "mail.activity/updated":
                    if (notif.payload.activity_created) {
                        this.store.activityCounter++;
                    }
                    if (notif.payload.activity_deleted) {
                        this.store.activityCounter--;
                    }
                    break;
                case "mail.channel/new_message":
                    this._handleNotificationNewMessage(notif);
                    break;
                case "mail.channel/leave":
                    {
                        const thread = this.threadService.insert({
                            ...notif.payload,
                            model: "mail.channel",
                        });
                        removeFromArray(this.store.discuss.channels.threads, thread.localId);
                        if (thread.localId === this.store.discuss.threadLocalId) {
                            this.store.discuss.threadLocalId = undefined;
                        }
                        this.notificationService.add(
                            sprintf(_t("You unsubscribed from %s."), thread.displayName),
                            { type: "info" }
                        );
                    }
                    break;
                case "mail.channel/rtc_sessions_update":
                    {
                        const { id, rtcSessions } = notif.payload;
                        const sessionsData = rtcSessions[0][1];
                        const command = rtcSessions[0][0];
                        this._updateRtcSessions(id, sessionsData, command);
                    }
                    break;
                case "mail.record/insert":
                    this._handleNotificationRecordInsert(notif);
                    break;
                case "mail.channel/joined": {
                    const { channel, invited_by_user_id: invitedByUserId } = notif.payload;
                    const thread = this.threadService.insert({
                        ...channel,
                        rtcSessions: channel.rtcSessions[0][1],
                        model: "mail.channel",
                        serverData: {
                            channel: channel.channel,
                        },
                        type: channel.channel.channel_type,
                    });
                    if (invitedByUserId !== this.store.user?.user.id) {
                        this.notificationService.add(
                            sprintf(_t("You have been invited to #%s"), thread.displayName),
                            { type: "info" }
                        );
                    }
                    break;
                }
                case "mail.channel/legacy_insert":
                    this.threadService.insert({
                        id: notif.payload.channel.id,
                        model: "mail.channel",
                        serverData: notif.payload,
                        type: notif.payload.channel.channel_type,
                    });
                    break;
                case "mail.channel/transient_message":
                    return this.messageService.createTransient(
                        Object.assign(notif.payload, { body: markup(notif.payload.body) })
                    );
                case "mail.link.preview/delete":
                    {
                        const { id, message_id } = notif.payload;
                        const index = this.store.messages[message_id].linkPreviews.findIndex(
                            (linkPreview) => linkPreview.id === id
                        );
                        delete this.store.messages[message_id].linkPreviews[index];
                    }
                    break;
                case "mail.message/inbox": {
                    const data = Object.assign(notif.payload, { body: markup(notif.payload.body) });
                    this.messageService.insert(data);
                    break;
                }
                case "mail.message/mark_as_read": {
                    const { message_ids: messageIds, needaction_inbox_counter } = notif.payload;
                    for (const messageId of messageIds) {
                        // We need to ignore all not yet known messages because we don't want them
                        // to be shown partially as they would be linked directly to cache.
                        // Furthermore, server should not send back all messageIds marked as read
                        // but something like last read messageId or something like that.
                        // (just imagine you mark 1000 messages as read ... )
                        const message = this.store.messages[messageId];
                        if (!message) {
                            continue;
                        }
                        // update thread counter (before removing message from Inbox, to ensure isNeedaction check is correct)
                        const originThread = message.originThread;
                        if (originThread && message.isNeedaction) {
                            originThread.message_needaction_counter--;
                        }
                        // move messages from Inbox to history
                        const partnerIndex = message.needaction_partner_ids.find(
                            (p) => p === this.store.user.id
                        );
                        removeFromArray(message.needaction_partner_ids, partnerIndex);
                        removeFromArrayWithPredicate(
                            this.store.discuss.inbox.messages,
                            ({ id }) => id === messageId
                        );
                        if (this.store.discuss.history.messages.length > 0) {
                            this.store.discuss.history.messages.push(message);
                        }
                    }
                    this.store.discuss.inbox.counter = needaction_inbox_counter;
                    if (
                        this.store.discuss.inbox.counter > this.store.discuss.inbox.messages.length
                    ) {
                        this.threadService.fetchMessages(this.store.discuss.inbox);
                    }
                    break;
                }
                case "mail.message/toggle_star": {
                    const { message_ids: messageIds, starred } = notif.payload;
                    for (const messageId of messageIds) {
                        const message = this.messageService.insert({ id: messageId });
                        this.messageService.updateStarred(message, starred);
                        this.messageService.sortMessages(this.store.discuss.starred);
                    }
                    break;
                }
                case "mail.channel.member/seen": {
                    const { channel_id, last_message_id, partner_id } = notif.payload;
                    const channel = this.store.threads[createLocalId("mail.channel", channel_id)];
                    if (!channel) {
                        // for example seen from another browser, the current one has no
                        // knowledge of the channel
                        return;
                    }
                    if (this.store.user.id === partner_id) {
                        channel.serverLastSeenMsgBySelf = last_message_id;
                    }
                    const seenInfo = channel.seenInfos.find(
                        (seenInfo) => seenInfo.partner.id === partner_id
                    );
                    if (seenInfo) {
                        seenInfo.lastSeenMessage = { id: last_message_id };
                    }
                    break;
                }

                case "mail.channel.member/fetched": {
                    const { channel_id, last_message_id, partner_id } = notif.payload;
                    const channel = this.store.threads[createLocalId("mail.channel", channel_id)];
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
                case "mail.channel.member/typing_status": {
                    const isTyping = notif.payload.isTyping;
                    const channel = this.store.threads[
                        createLocalId("mail.channel", notif.payload.channel.id)
                    ];
                    if (!channel) {
                        return;
                    }
                    const member = this.threadService.insertChannelMember(notif.payload);
                    if (member.persona === this.store.self) {
                        return;
                    }
                    if (isTyping) {
                        if (!channel.typingMembers.includes(member)) {
                            channel.typingMemberIds.push(member.id);
                        }
                        if (member.typingTimer) {
                            browser.clearTimeout(member.typingTimer);
                        }
                        member.typingTimer = browser.setTimeout(() => {
                            removeFromArray(channel.typingMemberIds, member.id);
                        }, OTHER_LONG_TYPING);
                    } else {
                        removeFromArray(channel.typingMemberIds, member.id);
                    }
                    break;
                }
                case "mail.channel/unpin": {
                    const thread = this.store.threads[
                        createLocalId("mail.channel", notif.payload.id)
                    ];
                    if (!thread) {
                        return;
                    }
                    this.threadService.remove(thread);
                    this.notificationService.add(
                        sprintf(_t("You unpinned your conversation with %s"), thread.displayName),
                        { type: "info" }
                    );
                    break;
                }
                case "mail.message/notification_update":
                    {
                        notif.payload.elements.map((message) => {
                            this.messageService.insert({
                                ...message,
                                body: markup(message.body),
                                // implicit: failures are sent by the server at
                                // initialization only if the current partner is
                                // author of the message
                                author: this.store.self,
                            });
                        });
                    }
                    break;
            }
        }
    }

    async _handleNotificationNewMessage(notif) {
        const { id, message: messageData } = notif.payload;
        let channel = this.store.threads[createLocalId("mail.channel", id)];
        if (!channel) {
            const [channelData] = await this.orm.call("mail.channel", "channel_info", [id]);
            channel = this.threadService.insert({
                id: channelData.id,
                model: "mail.channel",
                type: channelData.channel_type,
                serverData: channelData,
            });
        }
        if (!channel.is_pinned) {
            this.threadService.pin(channel);
        }

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
        if (channel.chatPartnerId !== this.store.partnerRoot?.id) {
            if (!this.presence.isOdooFocused() && channel.isChatChannel) {
                this.notifyOutOfFocusMessage(message, channel);
            }

            if (channel.type !== "channel" && !this.store.guest) {
                // disabled on non-channel threads and
                // on `channel` channels for performance reasons
                this.threadService.markAsFetched(channel);
            }
        }
        if (
            channel.composer.isFocused &&
            channel.mostRecentNonTransientMessage &&
            !this.store.guest &&
            channel.mostRecentNonTransientMessage === channel.mostRecentMsg
        ) {
            this.threadService.markAsRead(channel);
        }
    }

    _handleNotificationRecordInsert(notif) {
        if (notif.payload.Thread) {
            this.threadService.insert({
                id: notif.payload.Thread.id,
                model: notif.payload.Thread.model,
                serverData: notif.payload.Thread,
            });
        }
        if (notif.payload.RtcSession) {
            this.rtc.insertSession(notif.payload.RtcSession);
        }
        if (notif.payload.Partner) {
            const partners = Array.isArray(notif.payload.Partner)
                ? notif.payload.Partner
                : [notif.payload.Partner];
            for (const partner of partners) {
                if (partner.im_status) {
                    this.personaService.insert({ ...partner, type: "partner" });
                }
            }
        }
        if (notif.payload.Guest) {
            const guests = Array.isArray(notif.payload.Guest)
                ? notif.payload.Guest
                : [notif.payload.Guest];
            for (const guest of guests) {
                this.personaService.insert({ ...guest, type: "guest" });
            }
        }
        const { LinkPreview: linkPreviews } = notif.payload;
        if (linkPreviews) {
            for (const linkPreview of linkPreviews) {
                this.store.messages[linkPreview.message.id].linkPreviews.push(
                    new LinkPreview(linkPreview)
                );
            }
        }
        const { Message: messageData } = notif.payload;
        if (messageData) {
            this.messageService.insert({
                ...messageData,
                body: messageData.body ? markup(messageData.body) : messageData.body,
            });
        }
        const { "res.users.settings": settings } = notif.payload;
        if (settings) {
            this.userSettingsService.updateFromCommands(settings);
            this.store.discuss.chats.isOpen =
                settings.is_discuss_sidebar_category_chat_open ?? this.store.discuss.chats.isOpen;
            this.store.discuss.channels.isOpen =
                settings.is_discuss_sidebar_category_channel_open ??
                this.store.discuss.channels.isOpen;
        }
    }

    _updateRtcSessions(channelId, sessionsData, command) {
        const channel = this.store.threads[createLocalId("mail.channel", channelId)];
        if (!channel) {
            return;
        }
        const oldCount = Object.keys(channel.rtcSessions).length;
        switch (command) {
            case "insert-and-unlink":
                for (const sessionData of sessionsData) {
                    this.rtc.deleteSession(sessionData.id);
                }
                break;
            case "insert":
                for (const sessionData of sessionsData) {
                    const session = this.rtc.insertSession(sessionData);
                    channel.rtcSessions[session.id] = session;
                }
                break;
        }
        if (Object.keys(channel.rtcSessions).length > oldCount) {
            this.soundEffectsService.play("channel-join");
        } else if (Object.keys(channel.rtcSessions).length < oldCount) {
            this.soundEffectsService.play("member-leave");
        }
    }

    // -------------------------------------------------------------------------
    // actions that can be performed on the messaging system
    // -------------------------------------------------------------------------

    fetchPreviews = memoize(async () => {
        const ids = [];
        for (const thread of Object.values(this.store.threads)) {
            if (["channel", "group", "chat"].includes(thread.type)) {
                ids.push(thread.id);
            }
        }
        if (ids.length) {
            const previews = await this.orm.call("mail.channel", "channel_fetch_preview", [ids]);
            for (const preview of previews) {
                const thread = this.store.threads[createLocalId("mail.channel", preview.id)];
                const data = Object.assign(preview.last_message, {
                    body: markup(preview.last_message.body),
                });
                this.messageService.insert({ ...data, res_id: thread.id, model: thread.model });
            }
        }
    });

    async searchPartners(searchStr = "", limit = 10) {
        let partners = [];
        const searchTerm = cleanTerm(searchStr);
        for (const localId in this.store.personas) {
            const persona = this.store.personas[localId];
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
            const partnersData = await this.orm.silent.call("res.partner", "im_search", [
                searchTerm,
                limit,
            ]);
            partners = partnersData.map((data) =>
                this.personaService.insert({ ...data, type: "partner" })
            );
        }
        return partners;
    }

    openDocument({ id, model }) {
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            views: [[false, "form"]],
            res_id: id,
        });
    }

    insertCannedResponse(data) {
        let cannedResponse = this.store.cannedResponses[data.id];
        if (!cannedResponse) {
            this.store.cannedResponses[data.id] = new CannedResponse();
            cannedResponse = this.store.cannedResponses[data.id];
        }
        Object.assign(cannedResponse, {
            id: data.id,
            name: data.source,
            substitution: data.substitution,
        });
        return cannedResponse;
    }
}

export const messagingService = {
    dependencies: [
        "mail.store",
        "rpc",
        "orm",
        "user",
        "router",
        "bus_service",
        "im_status",
        "notification",
        "multi_tab",
        "presence",
        "mail.sound_effects",
        "mail.user_settings",
        "mail.thread",
        "mail.message",
        "mail.persona",
        "mail.rtc",
    ],
    async: asyncMethods,
    start(env, services) {
        // compute initial discuss thread
        let threadLocalId = createLocalId("mail.box", "inbox");
        const activeId = services.router.current.hash.active_id;
        if (typeof activeId === "number") {
            threadLocalId = createLocalId("mail.channel", activeId);
        }
        if (typeof activeId === "string" && activeId.startsWith("mail.box_")) {
            threadLocalId = createLocalId("mail.box", activeId.slice(9));
        }
        if (typeof activeId === "string" && activeId.startsWith("mail.channel_")) {
            threadLocalId = createLocalId("mail.channel", parseInt(activeId.slice(13), 10));
        }
        const messaging = new Messaging(env, services, threadLocalId);
        messaging.initialize();
        services.bus_service.addEventListener("notification", (notifEvent) => {
            messaging.handleNotification(notifEvent.detail);
        });
        services.bus_service.start();
        // debugging. remove this
        window.messaging = messaging;
        return messaging;
    },
};

registry.category("services").add("mail.messaging", messagingService);
