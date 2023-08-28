/* @odoo-module */

import { Persona } from "@mail/core/common/persona_model";
import { assignDefined, createLocalId, nullifyClearCommands } from "@mail/utils/common/misc";

import { registry } from "@web/core/registry";
import { useSequential } from "@mail/utils/common/hooks";
import { markRaw } from "@odoo/owl";

export const DEFAULT_AVATAR = "/mail/static/src/img/smiley/avatar.jpg";

export class PersonaService {
    constructor(...args) {
        this.setup(...args);
    }

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

    /**
     * @param {import("@mail/core/common/persona_model").Data} data
     * @returns {import("@mail/core/common/persona_model").Persona}
     */
    insert(data) {
        const localId = createLocalId(data.type, data.id);
        let persona = this.store.personas[localId];
        if (!persona) {
            persona = new Persona();
            persona._store = this.store;
            persona.localId = localId;
            this.store.personas[localId] = persona;
        }
        this.update(persona, data);
        // return reactive version
        return this.store.personas[localId];
    }

    update(persona, data) {
        nullifyClearCommands(data);
        assignDefined(persona, { ...data });
        if (
            persona.type === "partner" &&
            persona.im_status !== "im_partner" &&
            !persona.is_public &&
            !this.store.registeredImStatusPartners?.includes(persona.id)
        ) {
            this.store.registeredImStatusPartners?.push(persona.id);
        }
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
                this.insert({ id, is_company, type: "partner" });
                ongoing.delete(id);
                this._sQueue.todo.delete(id);
            }
            for (const id of ongoing) {
                // no is_company found => assumes persona is not a company
                this.insert({ id, is_company: false, type: "partner" });
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
    dependencies: ["orm", "rpc", "mail.store"],
    start(env, services) {
        return new PersonaService(env, services);
    },
};

registry.category("services").add("mail.persona", personaService);
