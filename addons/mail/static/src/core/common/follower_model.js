/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";

/**
 * @typedef Data
 * @property {import("@mail/core/common/thread_model").Thread} followedThread
 * @property {number} id
 * @property {Boolean} is_active
 * @property {import("@mail/core/common/partner_model").Data} partner
 */

export class Follower extends DiscussModel {
    static id = ["id"];

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
        return this.partner.equals(this._store.user)
            ? this.followedThread.hasReadAccess
            : hasWriteAccess;
    }
}

export class FollowerManager extends DiscussModelManager {
    /** @type {typeof Follower} */
    class;
    /** @type {Object.<number, Follower>} */
    records = {};

    /**
     * @param {Data} data
     * @returns {Follower}
     */
    insert(data) {
        let follower = this.records[data.id];
        if (!follower) {
            this.records[data.id] = new Follower();
            follower = this.records[data.id];
            follower.objectId = this._createObjectId(data);
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
}

discussModelRegistry.add("Follower", [Follower, FollowerManager]);
