/* @odoo-module */

import { createObjectId } from "@mail/utils/common/misc";
import { registry } from "@web/core/registry";

export const discussModelRegistry = registry.category("discuss.model");

export class DiscussModel {
    /**
     * property names whose value uniquely identify the object in the model
     *
     * @type {string[]}
     */
    static id = [];

    equals(record) {
        return record?.objectId === this.objectId;
    }
}

export class DiscussModelManager {
    /** @type {typeof DiscussModel} */
    class;
    nextId = 0;
    /** @type {Object.<number, DiscussModel>} */
    records = {};
    /** @type {import("@mail/core/common/store_service").Store} */
    store;

    constructor(env, store) {
        this.env = env;
        this.store = store;
    }

    /**
     * @param {Object|DiscussModel} data
     * @returns {string}
     */
    _createObjectId(data = {}) {
        if (data instanceof DiscussModel) {
            return data.objectId;
        }
        if (this.class.id.length === 0) {
            return createObjectId(this.class.name, this.nextId++);
        }
        return createObjectId(this.class.name, ...this.class.id.map((i) => data[i]));
    }

    /**
     * @param {Object} data
     * @returns {DiscussModel}
     */
    findById(data) {
        return this.records[this._createObjectId(data)];
    }

    insert(data) {
        const objectId = this._createObjectId(data);
        if (objectId in this.records) {
            const record = this.records[objectId];
            this.update(record, data);
            return record;
        }
        const record = new this.class(this.store, data);
        record.objectId = objectId;
        this.update(record, data);
        // return reactive version.
        return this.records[record.objectId];
    }

    update(record, data) {
        Object.assign(record, data);
    }
}

/**
 * Add this at end of file to register the discuss model
 * (replace `DiscussModel` by your model name)
 */
// discussModelRegistry.add("DiscussModel", [DiscussModel, DiscussModelManager]);
