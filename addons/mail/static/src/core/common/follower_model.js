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
    static id = "id";
    /** @type {Object.<number, Follower>} */
    static records = {};
    /**
     * @param {Data} data
     * @returns {Follower}
     */
    static insert(data) {
        let follower = this.get(data);
        if (!follower) {
            follower = this.new(data);
            this.records[follower.localId] = follower;
            follower = this.records[follower.localId];
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
    followedThread = Record.one();
    /** @type {number} */
    id;
    /** @type {boolean} */
    isActive;
    /** @type {import("@mail/core/common/persona_model").Persona} */
    partner = Record.one();
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
