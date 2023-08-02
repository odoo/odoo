/* @odoo-module */

import { DiscussModel } from "@mail/core/common/discuss_model";

export class ScrollPosition extends DiscussModel {
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
