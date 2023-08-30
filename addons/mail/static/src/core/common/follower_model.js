/* @odoo-module */

import { Record } from "@mail/core/common/record";

/**
 * @typedef Data
 * @property {import("@mail/core/common/thread_model").Thread} followedThread
 * @property {number} id
 * @property {Boolean} is_active
 * @property {import("@mail/core/common/partner_model").Data} partner
 */

export class Follower extends Record {
    /** @type {Object.<number, Follower>} */
    static records = {};
    /**
     * @param {Data} data
     * @returns {Follower}
     */
    static insert(data) {
        let follower = this.records[data.id];
        if (!follower) {
            this.records[data.id] = new Follower();
            follower = this.records[data.id];
        }
        Object.assign(follower, {
            followedThread: data.followedThread,
            id: data.id,
            isActive: data.is_active,
            partner: this.store.Persona.insert({ ...data.partner, type: "partner" }),
            _store: this.store,
        });
        return follower;
    }

    /** @type {import("@mail/core/common/thread_model").Thread} */
    followedThread;
    /** @type {number} */
    id;
    /** @type {boolean} */
    isActive;
    /** @type {import("@mail/core/common/persona_model").Persona} */
    partner;
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;

    /**
     * @returns {boolean}
     */
    get isEditable() {
        const hasWriteAccess = this.followedThread ? this.followedThread.hasWriteAccess : false;
        return this.partner.eq(this._store.user)
            ? this.followedThread.hasReadAccess
            : hasWriteAccess;
    }
}

Follower.register();
