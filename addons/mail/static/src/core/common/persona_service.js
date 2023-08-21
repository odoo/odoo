/* @odoo-module */

import { registry } from "@web/core/registry";

export const DEFAULT_AVATAR = "/mail/static/src/img/smiley/avatar.jpg";

export class PersonaService {
    constructor(...args) {
        this.setup(...args);
    }

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    setup(env, services) {
        this.env = env;
        this.rpc = services.rpc;
        /** @type {import("@mail/core/common/store_service").Store */
        this.store = services["mail.store"];
    }

    async updateGuestName(guest, name) {
        await this.rpc("/mail/guest/update_name", {
            guest_id: guest.id,
            name,
        });
    }

    /**
     * @param {import("@mail/core/common/persona_model").Data} data
     * @returns {import("@mail/core/common/persona_model").Persona}
     */
    insert(data) {
        return this.store.Persona.insert(data);
    }

    update(persona, data) {
        return this.store.Persona.update(persona, data);
    }

    /**
     * List of known partner ids with a direct chat, ordered
     * by most recent interest (1st item being the most recent)
     *
     * @returns {[integer]}
     */
    getRecentChatPartnerIds() {
        return Object.values(this.store.threads)
            .filter((thread) => thread.type === "chat")
            .sort((a, b) => {
                if (!a.lastInterestDateTime && !b.lastInterestDateTime) {
                    return 0;
                }
                if (a.lastInterestDateTime && !b.lastInterestDateTime) {
                    return -1;
                }
                if (!a.lastInterestDateTime && b.lastInterestDateTime) {
                    return 1;
                }
                return b.lastInterestDateTime.ts - a.lastInterestDateTime.ts;
            })
            .map((thread) => thread.chatPartnerId);
    }
}

export const personaService = {
    dependencies: ["rpc", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new PersonaService(env, services);
    },
};

registry.category("services").add("mail.persona", personaService);
