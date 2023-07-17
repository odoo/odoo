/* @odoo-module */

import { CannedResponse } from "@mail/core/common/canned_response_model";
import { LinkPreview } from "@mail/core/common/link_preview_model";
import { removeFromArray, removeFromArrayWithPredicate } from "@mail/utils/common/arrays";
import { cleanTerm } from "@mail/utils/common/format";

import { markup, reactive } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";

/**
 * @typedef {Messaging} Messaging
 */
export class Messaging {
    constructor(...args) {
        this.setup(...args);
    }

    setup(env, services) {
        this.env = env;
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        this.rpc = services.rpc;
        this.orm = services.orm;
        /** @type {import("@mail/core/common/attachment_service").AttachmentService} */
        this.attachmentService = services["mail.attachment"];
        /** @type {import("@mail/core/common/user_settings_service").UserSettings} */
        this.userSettingsService = services["mail.user_settings"];
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = services["mail.thread"];
        /** @type {import("@mail/core/common/message_service").MessageService} */
        this.messageService = services["mail.message"];
        /** @type {import("@mail/core/common/persona_service").PersonaService} */
        this.personaService = services["mail.persona"];
        this.router = services.router;
        this.bus = services.bus_service;
        this.isReady = new Deferred();
        this.imStatusService = services.im_status;
        const user = services.user;
        this.personaService.insert({ id: user.partnerId, type: "partner", isAdmin: user.isAdmin });
        this.registeredImStatusPartners = reactive([], () => this.updateImStatusRegistration());
        this.store.registeredImStatusPartners = this.registeredImStatusPartners;
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
        this.store.odoobot = this.personaService.insert({
            ...data.odoobot,
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
        this.store.discuss.isActive =
            data.menu_id === this.router.current.hash?.menu_id ||
            this.router.hash?.action === "mail.action_discuss";
        (data.shortcodes ?? []).forEach((code) => {
            this.insertCannedResponse(code);
        });
        this.store.hasLinkPreviewFeature = data.hasLinkPreviewFeature;
        this.store.initBusId = data.initBusId;
        this.isReady.resolve();
        this.store.isMessagingReady = true;
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
            this.store.notificationGroups.sort((n1, n2) => n2.lastMessage.id - n1.lastMessage.id);
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

    handleNotification(notifications) {
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
                case "mail.record/insert":
                    this._handleNotificationRecordInsert(notif);
                    break;
                case "mail.link.preview/delete":
                    {
                        const { id, message_id } = notif.payload;
                        removeFromArrayWithPredicate(
                            this.store.messages[message_id].linkPreviews,
                            (linkPreview) => linkPreview.id === id
                        );
                    }
                    break;
                case "mail.message/inbox": {
                    const data = Object.assign(notif.payload, { body: markup(notif.payload.body) });
                    const message = this.messageService.insert(data);
                    const inbox = this.store.discuss.inbox;
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
                        const message = this.store.messages[messageId];
                        if (!message) {
                            continue;
                        }
                        if (message.isNeedaction) {
                            removeFromArrayWithPredicate(
                                this.store.discuss.inbox.messages,
                                ({ id }) => id === message.id
                            );
                            this.store.discuss.inbox.counter--;
                        }
                        if (message.isStarred) {
                            removeFromArrayWithPredicate(
                                this.store.discuss.starred.messages,
                                ({ id }) => id === message.id
                            );
                            this.store.discuss.starred.counter--;
                        }
                        delete this.store.messages[messageId];
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
                    const inbox = this.store.discuss.inbox;
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
                            removeFromArrayWithPredicate(
                                originThread.needactionMessages,
                                ({ id }) => id === messageId
                            );
                        }
                        // move messages from Inbox to history
                        const partnerIndex = message.needaction_partner_ids.find(
                            (p) => p === this.store.user?.id
                        );
                        removeFromArray(message.needaction_partner_ids, partnerIndex);
                        removeFromArrayWithPredicate(inbox.messages, ({ id }) => id === messageId);
                        const history = this.store.discuss.history;
                        if (!history.messages.includes(message)) {
                            history.messages.push(message);
                        }
                    }
                    inbox.counter = needaction_inbox_counter;
                    if (inbox.counter > inbox.messages.length) {
                        this.threadService.fetchMoreMessages(inbox);
                    }
                    break;
                }
                case "mail.message/toggle_star": {
                    const { message_ids: messageIds, starred } = notif.payload;
                    for (const messageId of messageIds) {
                        const message = this.messageService.insert({ id: messageId });
                        this.messageService.updateStarred(message, starred);
                    }
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
                case "ir.attachment/delete":
                    {
                        const { id: attachmentId, message: messageData } = notif.payload;
                        if (messageData) {
                            this.messageService.insert({
                                ...messageData,
                            });
                        }
                        const attachment = this.store.attachments[attachmentId];
                        if (attachment) {
                            this.attachmentService.remove(attachment);
                        }
                    }
                    break;
            }
        }
    }

    _handleNotificationRecordInsert(notif) {
        if (notif.payload.Thread) {
            this.threadService.insert(notif.payload.Thread);
        }

        if (notif.payload.Channel) {
            this.threadService.insert({
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
                this.store.messages[linkPreview.message.id]?.linkPreviews.push(
                    new LinkPreview(linkPreview)
                );
            }
        }
        const { Message: messageData } = notif.payload;
        if (messageData) {
            const isStarred = this.store.messages[messageData.id]?.isStarred;
            const message = this.messageService.insert({
                ...messageData,
                body: messageData.body ? markup(messageData.body) : messageData.body,
            });
            if (isStarred && message.isEmpty) {
                this.messageService.updateStarred(message, false);
            }
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
        const { "res.users.settings.volumes": volumeSettings } = notif.payload;
        if (volumeSettings) {
            this.userSettingsService.setVolumes(volumeSettings);
        }
    }

    // -------------------------------------------------------------------------
    // actions that can be performed on the messaging system
    // -------------------------------------------------------------------------

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
        "mail.attachment",
        "mail.user_settings",
        "mail.thread",
        "mail.message",
        "mail.persona",
    ],
    start(env, services) {
        const messaging = new Messaging(env, services);
        messaging.initialize();
        messaging.isReady.then(() => {
            services.bus_service.addEventListener("notification", (notifEvent) => {
                messaging.handleNotification(notifEvent.detail);
            });
            services.bus_service.start();
        });
        return messaging;
    },
};

registry.category("services").add("mail.messaging", messagingService);
