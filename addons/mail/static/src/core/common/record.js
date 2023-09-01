/* @odoo-module */

import { toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

export class Record {
    static id;
    static __OR__ = Symbol("or");
    static __AND__ = Symbol("and");
    static records = {};
    /** @type {import("@mail/core/common/store_service").Store} */
    static store;
    static get(data) {
        return this.records[this.localId(data)];
    }
    static modelFromLocalId(localId) {
        return localId.split(",")[0];
    }
    static register() {
        modelRegistry.add(this.name, this);
    }
    static localId(data) {
        if (!data) {
            return undefined;
        }
        const modelName = this.name;
        let idStr;
        if (typeof data === "object") {
            idStr = this._localId(this.id, data);
        } else {
            idStr = data; // non-object data => single id
        }
        return [modelName, idStr].join(",");
    }
    static _localId(expr, data, { brackets = false } = {}) {
        if (!Array.isArray(expr)) {
            return data[expr];
        }
        const vals = [];
        for (let i = 1; i < expr.length; i++) {
            vals.push(this._localId(expr[i], data, { brackets: true }));
        }
        const res = vals.join(expr[0] === this.__OR__ ? " OR " : " AND ");
        if (brackets) {
            vals.unshift("(");
            vals.push(")");
        }
        return res;
    }
    /**
     * Technical attribute, DO NOT USE in business code.
     * This class is almost equivalent to current class of model,
     * except this is a function, so we can new() it, whereas
     * `this` is not, because it's an object.
     * (in order to comply with OWL reactivity)
     *
     * @type {typeof Record}
     */
    static Class;
    static AND(...args) {
        return [this.__AND__, ...args];
    }
    static OR(...args) {
        return [this.__OR__, ...args];
    }
    /**
     * This method is almost equivalent to new Class, except that it properly
     * setup relational fields of model with get/set, @see Class
     *
     * @returns {Record}
     */
    static new(data) {
        const obj = new this.Class();
        let record = Object.assign(obj, { localId: this.localId(data), Model: this });
        Object.assign(record, { _store: this.store });
        if (!Array.isArray(this.records)) {
            this.records[record.localId] = record;
            // return reactive version
            record = this.records[record.localId];
        }
        return record;
    }

    /**
     * @param {Object} data
     * @returns {Record}
     */
    static insert(data) {}

    /** @type {import("@mail/core/common/store_service").Store} */
    _store;
    /**
     * Technical attribute, contains the Model entry in the store.
     * This is almost the same as the class, except it's an object
     * (so it works with OWL reactivity), and it's the actual object
     * that store the records.
     *
     * Indeed, `this.constructor.records` is there to initiate `records`
     * on the store entry, but the class `static records` is not actually
     * used because it's non-reactive, and we don't want to persistently
     * store records on class, to make sure different tests do not share
     * records.
     *
     * @type {typeof Record}
     */
    Model;

    delete() {
        delete this.Model.records[this.localId];
        this.Model = null;
    }

    /** @param {Record} record */
    eq(record) {
        return toRaw(this) === toRaw(record);
    }

    /** @param {Record} record */
    notEq(record) {
        return !this.eq(record);
    }

    /** @param {Record[]} list */
    in(list) {
        if (!list) {
            return false;
        }
        return list.some((record) => record.eq(this));
    }

    /** @param {Record[]} list */
    notIn(list) {
        return !this.in(list);
    }
}

Record.register();
