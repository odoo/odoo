/* @odoo-module */

import {
    DiscussModel,
    DiscussModelManager,
    discussModelRegistry,
} from "@mail/core/common/discuss_model";

export class CannedResponse extends DiscussModel {
    static id = ["id"];

    /** @type {number} */
    id;
    /** @type {string} */
    name;
    /** @type {string} */
    substitution;
}

export class CannedResponseManager extends DiscussModelManager {
    /** @type {typeof CannedResponse} */
    class;
    /** @type {CannedResponse[]} */
    records = [];
}

discussModelRegistry.add("CannedResponse", [CannedResponse, CannedResponseManager]);
