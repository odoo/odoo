/** @odoo-module */

import { Record } from "@mail/core/record";

export class ScrollPosition extends Record {
    /** @type {number|undefined} */
    top;
    /** @type {number|undefined} */
    left;

    constructor(top, left) {
        super();
        this.top = top;
        this.left = left;
    }

    clear() {
        this.top = this.left = undefined;
    }

    get isSaved() {
        return this.top !== undefined || this.left !== undefined;
    }
}
