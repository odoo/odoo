/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class CannedResponse extends Record {
    /** @type {number} */
    id;
    /** @type {string} */
    name;
    /** @type {string} */
    substitution;
}
