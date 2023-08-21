/* @odoo-module */

import { Record, modelRegistry } from "@mail/core/common/record";

export class ScrollPosition extends Record {
    /** @type {Object.<number, ScrollPosition>} */
    static records = {};

    /** @type {number|undefined} */
    top;
    /** @type {number|undefined} */
    left;

    constructor(top, left) {
        super(top, left);
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

modelRegistry.add(ScrollPosition.name, ScrollPosition);
