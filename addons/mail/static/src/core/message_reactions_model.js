/** @odoo-module **/

export class MessageReactions {
    /** @type {string} */
    content;
    /** @type {number} **/
    count;
    /** @type {number[]} **/
    personaLocalIds = [];
    /** @type {number} **/
    messageId;
    /** @type {import("@mail/core/store_service").Store} */
    _store;

    /** @type {import("@mail/core/persona_model").Persona[]} */
    get personas() {
        return this.personaLocalIds.map((localId) => this._store.personas[localId]);
    }
}
