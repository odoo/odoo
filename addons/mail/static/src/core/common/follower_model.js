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
        return this._store.user === this.partner
            ? this.followedThread.hasReadAccess
            : hasWriteAccess;
    }
}

export class FollowerManager extends DiscussModelManager {
    /** @type {typeof Follower} */
    class;
    /** @type {Object.<number, Follower>} */
    records = {};
}

discussModelRegistry.add("Follower", [Follower, FollowerManager]);
