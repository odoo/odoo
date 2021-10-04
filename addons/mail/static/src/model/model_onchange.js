/** @odoo-module **/

export class OnChange {
    /**
     * Creates a new "on change" definition. This "on change" should be provided
     * to "onChanges" attribute of the concerned Model class to be notified of
     * changes in the given dependencies.
     *
     * @constructor
     * @param {Object} param
     * @param {string[]} param.dependencies a list of fields on the associated
     *  model to observe for change. x2one relational fields can be followed by
     *  using dot notation to have dependencies on their own fields too.
     * @param {string} param.methodName the name of a method on the associated
     *  model that will be called when one of the dependencies changes.
     */
    constructor({ dependencies, methodName }) {
        this.dependencies = dependencies;
        this.methodName = methodName;
    }

    /**
     * @returns {string}
     */
    toString() {
        return `onChange(${this.methodName})`;
    }
}
