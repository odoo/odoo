/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { createLocalId } from "../utils/misc";
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

    getThread(resModel, resId) {
        const localId = createLocalId(resModel, resId);
        if (localId in this.store.threads) {
            if (resId === false) {
                return this.store.threads[localId];
            }
            // to force a reload
            this.store.threads[localId].status = "new";
        }
        const thread = this.thread.insert({
            id: resId,
            model: resModel,
            type: "chatter",
        });
        if (resId === false) {
            const tmpId = `virtual${this.nextId++}`;
            const tmpData = {
                id: tmpId,
                author: { id: this.store.self.id },
                body: _t("Creating a new record..."),
                message_type: "notification",
                trackingValues: [],
                res_id: thread.id,
                model: thread.model,
            };
            this.message.insert(tmpData);
        }
        return thread;
    }
}

export const chatterService = {
    dependencies: ["mail.store", "mail.thread", "mail.message", "rpc", "orm", "mail.persona"],
    start(env, services) {
        return new ChatterService(env, services);
    },
};

registry.category("services").add("mail.chatter", chatterService);
