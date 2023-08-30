/* @odoo-module */

export class ScrollPosition {
    /** @type {number|undefined} */
    top;
    /** @type {number|undefined} */
    left;

    clear() {
        this.top = this.left = undefined;
    }

    get isSaved() {
        return this.top !== undefined || this.left !== undefined;
    }
}
