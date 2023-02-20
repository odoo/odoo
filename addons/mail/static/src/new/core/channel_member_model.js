/* @odoo-module */

import { createLocalId } from "../utils/misc";

/**
 * @class ChannelMember
 * @typedef Data
 * @property {number} id
 * @property {string} personaLocalId
 * @property {number} threadId
 */
export class ChannelMember {
    personaLocalId;
    threadId;
    typingTimer;
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;

    get persona() {
        return this._store.personas[this.personaLocalId];
    }

    set persona(persona) {
        this.personaLocalId = persona?.localId;
    }

    get thread() {
        return this._store.threads[createLocalId("mail.channel", this.threadId)];
    }

    get avatarUrl() {
        if (this.persona.type === "partner") {
            return `/mail/channel/${this.thread.id}/partner/${this.persona.id}/avatar_128`;
        }
        if (this.persona.type === "guest") {
            return `/mail/channel/${this.thread.id}/guest/${this.persona.id}/avatar_128?unique=${this.persona.name}`;
        }
        return "";
    }
}
