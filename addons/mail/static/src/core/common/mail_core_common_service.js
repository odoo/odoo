/* @odoo-module */

import { LinkPreview } from "@mail/core/common/link_preview_model";
import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";

import { markup, reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class MailCoreCommon {
    constructor(env, services) {
        Object.assign(this, {
            env,
            busService: services.bus_service,
        });
        /** @type {import("@mail/core/common/attachment_service").AttachmentService} */
        this.attachmentService = services["mail.attachment"];
        /** @type {import("@mail/core/common/message_service").MessageService} */
        this.messageService = services["mail.message"];
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        this.messagingService = services["mail.messaging"];
        /** @type {import("@mail/core/common/persona_service").PersonaService} */
        this.personaService = services["mail.persona"];
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = services["mail.thread"];
        /** @type {import("@mail/core/common/user_settings_service").UserSettings} */
        this.userSettingsService = services["mail.user_settings"];
    }

    setup() {
        this.messagingService.isReady.then(() => {
            this.busService.subscribe("ir.attachment/delete", (payload) => {
                const { id: attachmentId, message: messageData } = payload;
                if (messageData) {
                    this.messageService.insert({ ...messageData });
                }
                const attachment = this.store.attachments[attachmentId];
                if (attachment) {
                    this.attachmentService.remove(attachment);
                }
            });
            this.busService.subscribe("mail.link.preview/delete", (payload) => {
                const { id, message_id } = payload;
                const message = this.store.messages[message_id];
                if (message) {
                    removeFromArrayWithPredicate(
                        message.linkPreviews,
                        (linkPreview) => linkPreview.id === id
                    );
                }
            });
            this.busService.subscribe("mail.message/delete", (payload) => {
                for (const messageId of payload.message_ids) {
                    const message = this.store.messages[messageId];
                    if (!message) {
                        continue;
                    }
                    delete this.store.messages[messageId];
                    if (message.originThread) {
                        removeFromArrayWithPredicate(
                            message.originThread.messages,
                            ({ id }) => id === message.id
                        );
                    }
                    this.env.bus.trigger("mail.message/delete", { message });
                }
            });
            this.busService.subscribe("mail.message/notification_update", (payload) => {
                payload.elements.map((message) => {
                    this.messageService.insert({
                        ...message,
                        body: markup(message.body),
                        // implicit: failures are sent by the server at
                        // initialization only if the current partner is
                        // author of the message
                        author: this.store.self,
                    });
                });
            });
            this.busService.subscribe("mail.message/toggle_star", (payload) => {
                const { message_ids: messageIds, starred } = payload;
                for (const messageId of messageIds) {
                    const message = this.messageService.insert({ id: messageId });
                    this.messageService.updateStarred(message, starred);
                }
            });
            this.busService.subscribe("mail.record/insert", (payload) => {
                if (payload.Thread) {
                    this.threadService.insert(payload.Thread);
                }
                if (payload.Partner) {
                    const partners = Array.isArray(payload.Partner)
                        ? payload.Partner
                        : [payload.Partner];
                    for (const partner of partners) {
                        if (partner.im_status) {
                            this.personaService.insert({ ...partner, type: "partner" });
                        }
                    }
                }
                if (payload.Guest) {
                    const guests = Array.isArray(payload.Guest) ? payload.Guest : [payload.Guest];
                    for (const guest of guests) {
                        this.personaService.insert({ ...guest, type: "guest" });
                    }
                }
                const { LinkPreview: linkPreviews } = payload;
                if (linkPreviews) {
                    for (const linkPreview of linkPreviews) {
                        this.store.messages[linkPreview.message.id]?.linkPreviews.push(
                            new LinkPreview(linkPreview)
                        );
                    }
                }
                const { Message: messageData } = payload;
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
                const { "res.users.settings": settings } = payload;
                if (settings) {
                    this.userSettingsService.updateFromCommands(settings);
                }
            });
        });
    }
}

export const mailCoreCommon = {
    dependencies: [
        "bus_service",
        "mail.attachment",
        "mail.message",
        "mail.messaging",
        "mail.persona",
        "mail.store",
        "mail.thread",
        "mail.user_settings",
    ],
    start(env, services) {
        const mailCoreCommon = reactive(new MailCoreCommon(env, services));
        mailCoreCommon.setup();
        return mailCoreCommon;
    },
};

registry.category("services").add("mail.core.common", mailCoreCommon);
