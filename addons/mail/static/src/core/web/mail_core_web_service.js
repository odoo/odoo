/* @odoo-module */

import { markup, reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class MailCoreWeb {
    constructor(env, services) {
        /** @type {ReturnType<typeof import("@bus/services/bus_service").busService.start>} */
        this.busService = services["bus_service"];
        /** @type {import("@mail/core/common/message_service").MessageService} */
        this.messageService = services["mail.message"];
        /** @type {import("@mail/core/common/messaging_service").Messaging} */
        this.messagingService = services["mail.messaging"];
        /** @type {ReturnType<typeof import("@web/core/network/rpc_service").rpcService.start>} */
        this.rpc = services.rpc;
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
    }

    setup() {
        this.messagingService.isReady.then(() => {
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
                    (n1, n2) => n2.lastMessage.id - n1.lastMessage.id
                );
            });
            this.busService.start();
        });
    }
}

export const mailCoreWeb = {
    dependencies: ["bus_service", "mail.message", "mail.messaging", "mail.store", "rpc"],
    start(env, services) {
        const mailCoreWeb = reactive(new MailCoreWeb(env, services));
        mailCoreWeb.setup();
        return mailCoreWeb;
    },
};

registry.category("services").add("mail.core.web", mailCoreWeb);
