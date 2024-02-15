import { Record } from "@mail/core/common/record";

export class Follower extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").Follower>} */
    static records = {};
    /** @returns {import("models").Follower} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Follower|import("models").Follower[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    thread = Record.one("Thread");
    /** @type {number} */
    id;
    /** @type {boolean} */
    is_active;
    partner = Record.one("Persona");

    /** @returns {boolean} */
    get isEditable() {
        const hasWriteAccess = this.thread ? this.thread.hasWriteAccess : false;
        return this.partner.eq(this._store.self) ? this.thread.hasReadAccess : hasWriteAccess;
    }
}

Follower.register();
