/** @odoo-module **/

export class Listener {
    /**
     * Creates a new listener for handling changes in models. This listener
     * should be provided to the listening methods of the model manager.
     *
     * @constructor
     * @param {Object} param
     * @param {function} param.onChange function that will be called when this
     *  listener is notified of change, which is when records or fields that are
     *  listened to are created/updated/deleted. This function is called with
     *  1 param that contains info
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
    constructor({ onChange, isPartOfUpdateCycle = false }) {
        this.onChange = onChange;
        this.isPartOfUpdateCycle = isPartOfUpdateCycle;
    }
}
