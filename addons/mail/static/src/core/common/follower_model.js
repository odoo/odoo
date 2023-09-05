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
    /** @returns {Follower} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {Follower} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Data} data
     * @returns {Follower}
     */
    static insert(data) {
        const follower = this.get(data) ?? this.new(data);
        Object.assign(follower, {
            followedThread: data.followedThread,
            id: data.id,
            isActive: data.is_active,
            partner: this.store.Persona.insert({ ...data.partner, type: "partner" }),
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
