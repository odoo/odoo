/* @odoo-module */

/**
 * @typedef Data
 * @property {import("@mail/core/thread_model").Thread} followedThread
 * @property {number} id
 * @property {Boolean} is_active
 * @property {import("@mail/core/partner_model").Data} partner
 */

export class Follower {
    /** @type {import("@mail/core/thread_model").Thread} */
    followedThread;
    /** @type {number} */
    id;
    /** @type {boolean} */
    isActive;
    /** @type {import("@mail/core/persona_model").Persona} */
    partner;
    /** @type {import("@mail/core/store_service").Store} */
    _store;

    /**
     * @returns {boolean}
     */
    get isEditable() {
        const hasWriteAccess = this.followedThread ? this.followedThread.hasWriteAccess : false;
        return this._store.user === this.partner
            ? this.followedThread.hasReadAccess
            : hasWriteAccess;
    }
}
