/* @odoo-module */

import { registry } from "@web/core/registry";

export const discussModelRegistry = registry.category("discuss.model");

export class DiscussModel {}

export class DiscussModelManager {
    /** @type {typeof DiscussModel} */
    class;
    /** @type {Object.<number, DiscussModel>} */
    records = {};
    /** @type {import("@mail/core/common/store_service").Store} */
    store;

    constructor(store) {
        this.store = store;
    }
}

/**
 * Add this at end of file to register the discuss model
 * (replace `DiscussModel` by your model name)
 */
// discussModelRegistry.add("DiscussModel", [DiscussModel, DiscussModelManager]);
