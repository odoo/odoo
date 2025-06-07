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
        this.store = services["mail.store"];
    }

    setup() {
        this.busService.subscribe("ir.attachment/delete", (payload) => {
            const { id: attachmentId, message: messageData } = payload;
            if (messageData) {
                this.store.Message.insert(messageData);
            }
            const attachment = this.store.Attachment.get(attachmentId);
            attachment?.delete();
        });
        this.busService.subscribe("mail.message/delete", (payload, { id: notifId }) => {
            for (const messageId of payload.message_ids) {
                const message = this.store.Message.get(messageId);
                if (!message) {
                    continue;
                }
                this.env.bus.trigger("mail.message/delete", { message, notifId });
                message.delete();
            }
        });
        this.busService.subscribe("mail.message/toggle_star", (payload, metadata) =>
            this._handleNotificationToggleStar(payload, metadata)
        );
        this.busService.subscribe("res.users.settings", (payload) => {
            if (payload) {
                this.store.settings.update(payload);
            }
        });
        this.busService.subscribe("mail.record/insert", (payload) => {
            this.store.insert(payload, { html: true });
        });
    }

    _handleNotificationToggleStar(payload, metadata) {
        const { message_ids: messageIds, starred } = payload;
        this.store.Message.insert(messageIds.map((id) => ({ id, starred })));
    }
}

export const mailCoreCommon = {
    dependencies: ["bus_service", "mail.store"],
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
