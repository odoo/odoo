/** @odoo-module alias=@mail/../tests/helpers/command default=false */

export class Command {
    /**
     * @param {number} id
     */
    static link(id) {
        return [4, id, 0];
    }

    /**
     * @param {number} id
     */
    static unlink(id) {
        return [3, id, 0];
    }

    /**
     * @param {object} values
     */
    static create(values) {
        return [0, 0, values];
    }

    /**
     *
     * @param {number} id
     * @param {object} values
     */
    static update(id, values) {
        return [1, id, values];
    }

    /**
     * @param {object} values
     */
    static delete(id) {
        return [2, id, 0];
    }

    static clear() {
        return [5, 0, 0];
    }

    /**
     * @param {number[]} ids
     */
    static set(ids) {
        return [6, 0, ids];
    }
}
