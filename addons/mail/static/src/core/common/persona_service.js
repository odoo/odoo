/* @odoo-module */

import { Persona } from "@mail/core/common/persona_model";
import { assignDefined, createLocalId, nullifyClearCommands } from "@mail/utils/common/misc";
import { makeFnPatchable } from "@mail/utils/common/patch";

import { registry } from "@web/core/registry";

export const DEFAULT_AVATAR = "/mail/static/src/img/smiley/avatar.jpg";

let rpc;
/** @type {import("@mail/core/common/store_service").Store} */
let store;

/**
 * List of known partner ids with a direct chat, ordered
 * by most recent interest (1st item being the most recent)
 *
 * @returns {[integer]}
 */
export function getRecentChatPartnerIds() {
    return Object.values(store.threads)
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

/**
 * @param {import("@mail/core/common/persona_model").Data} data
 * @returns {import("@mail/core/common/persona_model").Persona}
 */
export function insertPersona(data) {
    const localId = createLocalId(data.type, data.id);
    let persona = store.personas[localId];
    if (!persona) {
        persona = new Persona();
        persona._store = store;
        persona.localId = localId;
        store.personas[localId] = persona;
    }
    updatePersona(persona, data);
    // return reactive version
    return store.personas[localId];
}

export async function updateGuestName(guest, name) {
    await rpc("/mail/guest/update_name", {
        guest_id: guest.id,
        name,
    });
}

export const updatePersona = makeFnPatchable(function (persona, data) {
    nullifyClearCommands(data);
    assignDefined(persona, { ...data });
    if (
        persona.type === "partner" &&
        persona.im_status !== "im_partner" &&
        !persona.is_public &&
        !store.registeredImStatusPartners?.includes(persona.id)
    ) {
        store.registeredImStatusPartners?.push(persona.id);
    }
});

export class PersonaService {
    constructor(...args) {
        this.setup(...args);
    }

    setup(env, services) {
        this.env = env;
        rpc = services.rpc;
        store = services["mail.store"];
    }
}

export const personaService = {
    dependencies: ["rpc", "mail.store"],
    start(env, services) {
        return new PersonaService(env, services);
    },
};

registry.category("services").add("mail.persona", personaService);
