/* @odoo-module */

import { removeFromArrayWithPredicate } from "@mail/utils/common/arrays";

import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class MailCoreCommon {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.attachmentService = services["mail.attachment"];
        this.messageService = services["mail.message"];
        this.messagingService = services["mail.messaging"];
        this.store = services["mail.store"];
        this.userSettingsService = services["mail.user_settings"];
    }

    setup() {
        this.messagingService.isReady.then(() => {
            this.busService.subscribe("ir.attachment/delete", (payload) => {
                const { id: attachmentId, message: messageData } = payload;
                if (messageData) {
                    this.store.Message.insert({ ...messageData });
                }
                const attachment = this.store.Attachment.get(attachmentId);
                if (attachment) {
                    this.attachmentService.remove(attachment);
                }
            });
            this.busService.subscribe("mail.link.preview/delete", (payload) => {
                const { id, message_id } = payload;
                const message = this.store.Message.get(message_id);
                if (message) {
                    removeFromArrayWithPredicate(
                        message.linkPreviews,
                        (linkPreview) => linkPreview.id === id
                    );
                }
            });
            this.busService.subscribe("mail.message/delete", (payload) => {
                for (const messageId of payload.message_ids) {
                    const message = this.store.Message.get(messageId);
                    if (!message) {
                        continue;
                    }
                    this.env.bus.trigger("mail.message/delete", { message });
                    message.delete();
                }
            });
            this.busService.subscribe("mail.message/notification_update", (payload) => {
                payload.elements.map((message) => {
                    this.store.Message.insert(
                        {
                            ...message,
                            // implicit: failures are sent by the server at
                            // initialization only if the current partner is
                            // author of the message
                            author: this.store.self,
                        },
                        { html: true }
                    );
                });
            });
            this.busService.subscribe("mail.message/toggle_star", (payload) => {
                const { message_ids: messageIds, starred } = payload;
                for (const messageId of messageIds) {
                    const message = this.store.Message.insert({ id: messageId });
                    message.isStarred = starred;
                    const starredBox = this.store.discuss.starred;
                    if (starred) {
                        starredBox.counter++;
                        starredBox.messages.add(message);
                    } else {
                        starredBox.counter--;
                        starredBox.messages.delete(message);
                    }
                }
            });
            this.busService.subscribe("res.users.settings", (payload) => {
                if (payload) {
                    this.userSettingsService.updateFromCommands(payload);
                }
            });
            this.busService.subscribe("mail.record/insert", (payload) => {
                if (payload.Thread) {
                    this.store.Thread.insert(payload.Thread);
                }
                if (payload.Persona) {
                    const personas = Array.isArray(payload.Persona)
                        ? payload.Persona
                        : [payload.Persona];
                    for (const persona of personas) {
                        this.store.Persona.insert(persona);
                    }
                }
                const { LinkPreview: linkPreviews } = payload;
                if (linkPreviews) {
                    for (const linkPreview of linkPreviews) {
                        this.store.LinkPreview.insert(linkPreview);
                    }
                }
                const { Message: messageData } = payload;
                if (messageData) {
                    this.store.Message.insert(messageData, { html: true });
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
        "mail.store",
        "mail.user_settings",
    ],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        const mailCoreCommon = reactive(new MailCoreCommon(env, services));
        mailCoreCommon.setup();
        return mailCoreCommon;
    },
};

registry.category("services").add("mail.core.common", mailCoreCommon);
