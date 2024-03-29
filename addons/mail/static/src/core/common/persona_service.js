/* @odoo-module */

import { registry } from "@web/core/registry";
import { useSequential } from "@mail/utils/common/hooks";
import { markRaw } from "@odoo/owl";
import { compareDatetime } from "@mail/utils/common/misc";

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
        this.orm = services.orm;
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = services["mail.store"];
        this.sequential = useSequential();
        /** Queue used for handling sequential of fetching is_company of persona */
        this._sQueue = markRaw({
            /** @type {Set<number>} */
            todo: new Set(),
        });
    }

    async updateGuestName(guest, name) {
        await this.rpc("/mail/guest/update_name", {
            guest_id: guest.id,
            name,
        });
    }

    async fetchIsCompany(persona) {
        if (persona.type !== "partner") {
            // non-partner persona are always considered as not a company
            persona.is_company = false;
            return;
        }
        this._sQueue.todo.add(persona.id);
        await new Promise(setTimeout); // group synchronous request to fetch is_company
        await this.sequential(async () => {
            const ongoing = new Set();
            if (this._sQueue.todo.size === 0) {
                return;
            }
            // load 'todo' into 'ongoing'
            this._sQueue.todo.forEach((id) => ongoing.add(id));
            this._sQueue.todo.clear();
            // fetch is_company
            const partnerData = await this.orm.silent.read(
                "res.partner",
                [...ongoing],
                ["is_company"],
                {
                    context: { active_test: false },
                }
            );
            for (const { id, is_company } of partnerData) {
                this.store.Persona.insert({ id, is_company, type: "partner" });
                ongoing.delete(id);
                this._sQueue.todo.delete(id);
            }
            for (const id of ongoing) {
                // no is_company found => assumes persona is not a company
                this.store.Persona.insert({ id, is_company: false, type: "partner" });
                this._sQueue.todo.delete(id);
            }
        });
    }

    /**
     * List of known partner ids with a direct chat, ordered
     * by most recent interest (1st item being the most recent)
     *
     * @returns {[integer]}
     */
    getRecentChatPartnerIds() {
        return Object.values(this.store.Thread.records)
            .filter((thread) => thread.type === "chat")
            .sort(
                (a, b) =>
                    compareDatetime(b.lastInterestDateTime, a.lastInterestDateTime) || b.id - a.id
            )
            .map((thread) => thread.chatPartner?.id);
    }
}

export const personaService = {
    dependencies: ["orm", "rpc", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new PersonaService(env, services);
    },
};

registry.category("services").add("mail.persona", personaService);
