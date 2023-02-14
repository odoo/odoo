/** @odoo-module */

import { registry } from "@web/core/registry";

export class ChatterService {
    constructor(env, services) {
        this.env = env;
        /** @type {import("@mail/new/core/store_service").Store} */
        this.store = services["mail.store"];
        /** @type {import("@mail/new/core/thread_service").ThreadService} */
        this.thread = services["mail.thread"];
        /** @type {import("@mail/new/core/message_service").MessageService} */
        this.message = services["mail.message"];
        this.rpc = services.rpc;
        this.orm = services.orm;
        /** @type {import("@mail/new/core/persona_service").PersonaService} */
        this.persona = services["mail.persona"];
    }
}

export const chatterService = {
    dependencies: ["mail.store", "mail.thread", "mail.message", "rpc", "orm", "mail.persona"],
    start(env, services) {
        return new ChatterService(env, services);
    },
};

registry.category("services").add("mail.chatter", chatterService);
