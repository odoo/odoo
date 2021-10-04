/** @odoo-module **/

export class Listener {
    /**
     * Creates a new listener for handling changes in models. This listener
     * should be provided to the listening methods of the model manager.
     *
     * @constructor
     * @param {Object} param
     * @param {string} param.name name of this listener, useful for debugging
     * @param {function} param.onChange function that will be called when this
     *  listener is notified of change, which is when records or fields that are
     *  listened to are created/updated/deleted. This function is called with
     *  1 param that contains info
     * @param {boolean} [param.isLocking=true] whether the model manager should
     *  be locked while this listener is observing, which means no change of
     *  state in any model is allowed (preventing to call insert/update/delete).
     * @param {boolean} [param.isPartOfUpdateCycle=false] determines at which
     *  point during the update cycle of the models this `onChange` function
     *  will be called.
     *  Note: a function called as part of the update cycle cannot have any side
     *  effect (such as updating a record), so it is usually necessary to keep
     *  this value to false. Keeping it to false also improves performance by
     *  making sure all side effects of update cycle (such as the update of
     *  computed fields) have been processed before `onChange` is called (it
     *  could otherwise be called multiple times in quick succession).
     */
    constructor({ name, onChange, isLocking = true, isPartOfUpdateCycle = false }) {
        this.isLocking = isLocking;
        this.isPartOfUpdateCycle = isPartOfUpdateCycle;
        this.name = name;
        this.onChange = onChange;
        // Set of last observed elements, for debugging purposes.
        this.lastObservedLocalIds = new Set();
        this.lastObservedFields = new Set();
    }

    /**
     * @returns {string}
     */
    toString() {
        return `listener(${this.name})`;
    }
}
