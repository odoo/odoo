/* @odoo-module */

import { Record } from "@mail/core/common/record";

/**
 * @typedef Data
 * @property {import("models").Thread} followedThread
 * @property {number} id
 * @property {Boolean} is_active
 * @property {import("@mail/core/common/persona_model").Data} partner
 */

export class Follower extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Models["Follower"]>} */
    static records = {};
    /** @returns {import("models").Models["Follower"]} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {import("models").Models["Follower"]} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Data} data
     * @returns {import("models").Models["Follower"]}
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

    followedThread = Record.one("Thread");
    /** @type {number} */
    id;
    /** @type {boolean} */
    isActive;
    partner = Record.one("Persona");

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
