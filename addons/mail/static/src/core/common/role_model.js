import { Record } from "@mail/core/common/record";

/**
 * @property {number} id
 * @property {string} name
 */

export class Role extends Record {
    static id = "id";

    /** @type {Object.<number, import("models").Role>} */
    static records = {};
    /** @returns {import("models").Role} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").Role|import("models").Role[]} */
    static insert(data) {
        return super.insert(...arguments);
    }

    /** @type {string} */
    name;
}

Role.register();
