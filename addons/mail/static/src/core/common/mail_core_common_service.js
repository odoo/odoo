import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class MailCoreCommon {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
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
                this.store["mail.message"].insert(messageData);
            }
            const attachment = this.store["ir.attachment"].get(attachmentId);
            attachment?.delete();
        });
        this.busService.subscribe("mail.message/delete", (payload, { id: notifId }) => {
            for (const messageId of payload.message_ids) {
                const message = this.store["mail.message"].get(messageId);
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
        this.busService.subscribe("mail.message/new", async (payload, metadata) => {
            const { data } = payload;
            this.store.insert(data);
            this._handleNotificationNewMessage(payload, metadata);
        });
        this.busService.subscribe("mail.record/insert", (payload) => {
            const { ignore_user_ids, ...message } = payload;
            if (!ignore_user_ids || !ignore_user_ids.includes(this.store.self.userId)) {

                this.store.insert(message);
            }
        });
    }

    _handleNotificationToggleStar(payload, metadata) {
        const { message_ids: messageIds, starred } = payload;
        this.store["mail.message"].insert(messageIds.map((id) => ({ id, starred })));
    }

    async _handleNotificationNewMessage(payload, { id: notifId }) {
        const { data, id: threadId, temporary_id } = payload;
        const model = data["mail.thread"][0].model;
        const thread = await this.store.Thread.getOrFetch({
            model,
            id: threadId,
        });
        if (!thread) {
            return;
        }
        const message = this.store["mail.message"].get(data["mail.message"][0]);
        if (!message) {
            return;
        }
        if (message.notIn(thread.messages)) {
            if (!thread.loadNewer) {
                thread.addOrReplaceMessage(message, this.store["mail.message"].get(temporary_id));
            } else if (thread.status === "loading") {
                thread.pendingNewMessages.push(message);
            }
            if (message.isSelfAuthored) {
                thread.onNewSelfMessage(message);
            }
        }
    }
}

export const mailCoreCommon = {
    dependencies: ["bus_service", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        const mailCoreCommon = reactive(new MailCoreCommon(env, services));
        mailCoreCommon.setup();
        return mailCoreCommon;
    },
};

registry.category("services").add("mail.core.common", mailCoreCommon);
