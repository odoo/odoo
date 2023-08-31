/* @odoo-module */

import { toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

export class Record {
    static id;
    static records = {};
    static __MANY__ = Symbol("many");
    static __ONE__ = Symbol("one");
    static __OR__ = Symbol("or");
    static __AND__ = Symbol("and");
    static get(data) {
        return this.records[this.localId(data)];
    }
    static modelFromLocalId(localId) {
        return localId.split(",")[0];
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
            if (this.Class.__rels__.has(expr)) {
                // relational field (note: optional when OR)
                return `(${data[expr]?.localId})`;
            }
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
     * except that prototype is enriched with get/set on relational fields.
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
    static many() {
        return this.__MANY__;
    }
    static one() {
        return this.__ONE__;
    }
    static register() {
        modelRegistry.add(this.name, this);
    }
    /**
     * This method is almost equivalent to new Class, except that it properly
     * setup relational fields of model with get/set, @see Class
     *
     * @returns {Record}
     */
    static new(data) {
        const obj = new this.Class();
        return Object.assign(obj, { localId: this.localId(data) });
    }
    /**
     * Raw relational values of the record, each of which contains object id(s)
     * rather than the record(s). This allows data in store and models being normalized,
     * which eases handling relations notably in when a record gets deleted.
     *
     * @type {Map<string, any>}
     */
    __rels__ = new Map();

    /**
     * @param {Object} data
     * @returns {Record}
     */
    static insert(data) {}

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
