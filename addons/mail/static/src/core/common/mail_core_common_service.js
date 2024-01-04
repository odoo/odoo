/* @odoo-module */

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
    }

    setup() {
        this.messagingService.isReady.then(() => {
            this.busService.subscribe("ir.attachment/delete", (payload) => {
                const { id: attachmentId, message: messageData } = payload;
                if (messageData) {
                    this.store.Message.insert(messageData);
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
                    message.linkPreviews.delete({ id });
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
                this.store.Message.insert(payload.elements, { html: true });
            });
            this.busService.subscribe("mail.message/toggle_star", (payload) => {
                const { message_ids: messageIds, starred } = payload;
                for (const messageId of messageIds) {
                    const message = this.store.Message.insert({ id: messageId });
                    const starredBox = this.store.discuss.starred;
                    if (starred) {
                        starredBox.counter++;
                        message.starredPersonas.add(this.store.self);
                        starredBox.messages.add(message);
                    } else {
                        starredBox.counter--;
                        message.starredPersonas.delete(this.store.self);
                        starredBox.messages.delete(message);
                    }
                }
            });
            this.busService.subscribe("res.users.settings", (payload) => {
                if (payload) {
                    this.store.settings.update(payload);
                }
            });
            this.busService.subscribe("mail.record/insert", (payload) => {
                for (const Model in payload) {
                    this.store[Model].insert(payload[Model], { html: true });
                }
            });
            this.busService.subscribe("mail.record/delete", (payload) => {
                for (const Model in payload) {
                    for (const data of payload[Model]) {
                        const record = this.store[Model].get(data);
                        record?.delete();
                    }
                }
            });
            this.busService.addEventListener("notification", ({ detail: notifications }) => {
                for (const notif of notifications.filter(
                    ({ type }) => type === "mail.thread/new_message"
                )) {
                    const messageFormat = JSON.parse(JSON.stringify(notif.payload));
                    this.store.Message.get(messageFormat.temporary_id)?.delete();
                    delete messageFormat.temporary_id;
                    const message = this.store.Message.insert(messageFormat, { html: true });
                    message.originThread.addNewMessage(message, {
                        afterInitBus: notif.id > this.store.initBusId,
                    });
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
