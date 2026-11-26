import { BusPlugin } from "@bus/services/bus_plugin";
import { StorePlugin } from "@mail/core/common/store_plugin";

import { Plugin, usePlugin } from "@odoo/owl";

import { GlobalBusPlugin } from "@web/core/global_bus_plugin";
import { services } from "@web/core/services";

export class MailCoreCommonPlugin extends Plugin {
    /** Started with the store it uses (see `StorePlugin`). */
    static sequence = 110;

    #busService = usePlugin(BusPlugin);
    #bus = usePlugin(GlobalBusPlugin).bus;
    #store = usePlugin(StorePlugin);

    setup() {
        this.#busService.subscribe("ir.attachment/delete", (payload) => {
            const { id: attachmentId, message: messageData } = payload;
            if (messageData) {
                this.#store["mail.message"].insert(messageData);
            }
            const attachment = this.#store["ir.attachment"].get(attachmentId);
            attachment?.delete();
        });
        this.#busService.subscribe("mail.message/delete", (payload, { id: notifId }) => {
            for (const messageId of payload.message_ids) {
                const message = this.#store["mail.message"].get(messageId);
                if (!message) {
                    continue;
                }
                this.#bus.trigger("mail.message/delete", { message, notifId });
                message.delete();
            }
        });
        this.#busService.subscribe("mail.record/insert", (payload) => {
            this.#store.insert(payload);
        });
        this.#bus.addEventListener(
            "discuss.channel/new_message",
            ({ detail: { channel, message, silent } }) => {
                if (this.#store.ui.isSmall() || message.isSelfAuthored || silent) {
                    return;
                }
                channel.notifyMessageToUser(message);
            }
        );
    }
}

services.add(MailCoreCommonPlugin);
