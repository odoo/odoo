/* @odoo-module */

import { DiscussModel } from "@mail/core/common/discuss_model";

export class CannedResponse extends DiscussModel {
    /** @type {number} */
    id;
    /** @type {string} */
    name;
    /** @type {string} */
    substitution;
}
