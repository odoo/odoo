/* @odoo-module */

import { toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

const MANY_LIST_SYM = Symbol("many-list");
const MANY_SET_SYM = Symbol("many-set");
const ONE_SYM = Symbol("one");
const OR_SYM = Symbol("or");
const AND_SYM = Symbol("and");

export function AND(...args) {
    return [AND_SYM, ...args];
}
export function OR(...args) {
    return [OR_SYM, ...args];
}

export class RecordInverses {
    /**
     * Track the inverse of a record. Each record contains this map.
     * - Key: localId of target record
     * - Value: Map where key is field name, and value is number of
     *          time current record is present in relation.
     *
     * @type {Map<string, Map<string, number>>}}
     */
    __map__ = new Map();
    /**
     * @param {string} localId
     * @param {string} name
     */
    add(localId, name) {
        if (!this.__map__.has(localId)) {
            this.__map__.set(localId, new Map());
        }
        const inv = this.__map__.get(localId);
        if (!inv.get(name)) {
            inv.set(name, 0);
        }
        inv.set(name, inv.get(name) + 1);
    }
    /**
     * @param {string} localId
     * @param {string} name
     */
    delete(localId, name) {
        if (!this.__map__.has(localId)) {
            return;
        }
        const inv = this.__map__.get(localId);
        if (!inv.get(name)) {
            return;
        }
        inv.set(name, inv.get(name) - 1);
        if (inv.get(name) === 0) {
            inv.delete(name);
        }
    }
}

/**
 * @template {Record} R
 * @augments RecordCollection
 */
export class RecordList extends Array {
    /** @type {string[]} */
    __list__ = [];

    constructor() {
        super();
        return new Proxy(this, {
            get(target, name, receiver) {
                if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                    // support for "array[index]" syntax
                    const index = parseInt(name);
                    return receiver.__store__.get(receiver.__list__[index]);
                }
                if (name === "length") {
                    return receiver.__list__.length;
                }
                return Reflect.get(target, name, receiver);
            },
            set(target, name, val, receiver) {
                if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                    // support for "array[index] = r3" syntax
                    const index = parseInt(name);
                    /** @type {R} */
                    const r3 = val;
                    const r2 = receiver[index];
                    if (r2 && r2.notEq(r3)) {
                        receiver.__deleteInverse__(r2);
                    }
                    receiver.__list__[index] = r3?.localId;
                    if (r3) {
                        receiver.__addInverse__(r3);
                    }
                } else if (name === "length") {
                    const newLength = parseInt(val);
                    if (newLength < receiver.length) {
                        receiver.splice(newLength, receiver.length - newLength);
                    }
                    receiver.__list__.length = newLength;
                } else {
                    Reflect.set(target, name, val, receiver);
                }
                return true;
            },
        });
    }

    /** @param {R[]} records */
    push(...records) {
        this.__list__.push(...records.map((r3) => r3.localId));
        for (const r3 of records) {
            if (r3) {
                this.__addInverse__(r3);
            }
        }
        return this.__list__.length;
    }
    /** @returns {R} */
    pop() {
        const r2 = this.__store__.get(this.__list__.pop());
        if (r2) {
            this.__deleteInverse__(r2);
        }
        return r2;
    }
    /** @returns {R} */
    shift() {
        const r2 = this.__store__.get(this.__list__.shift());
        if (r2) {
            this.__deleteInverse__(r2);
        }
        return r2;
    }
    /** @param {R[]} records */
    unshift(...records) {
        this.__list__.unshift(...records.map((r3) => r3.localId));
        for (const r3 of records) {
            if (r3) {
                this.__addInverse__(r3);
            }
        }
        return this.__list__.length;
    }
    /**
     * @param {Function} func
     * @returns {R[]}
     */
    map(func) {
        return this.__list__.map((localId) => func(this.__store__.get(localId)));
    }
    /**
     * @param {Function} predicate
     * @returns {R[]}
     */
    filter(predicate) {
        return this.__list__
            .filter((localId) => predicate(this.__store__.get(localId)))
            .map((localId) => this.__store__.get(localId));
    }
    /** @param {Function} predicate */
    some(predicate) {
        return this.__list__.some((localId) => predicate(this.__store__.get(localId)));
    }
    /** @param {Function} predicate */
    every(predicate) {
        return this.__list__.every((localId) => predicate(this.__store__.get(localId)));
    }
    /**
     * @param {Function} predicate
     * @returns {R}
     */
    find(predicate) {
        return this.__store__.get(
            this.__list__.find((localId) => predicate(this.__store__.get(localId)))
        );
    }
    /** @param {Function} predicate */
    findIndex(predicate) {
        return this.__list__.findIndex((localId) => predicate(this.__store__.get(localId)));
    }
    /** @param {R} record */
    indexOf(record) {
        return this.__list__.indexOf(record?.localId);
    }
    /** @param {R} record */
    includes(record) {
        return this.__list__.includes(record.localId);
    }
    /**
     * @param {number} [start]
     * @param {number} [end]
     * @returns {R[]}
     */
    slice(start, end) {
        return this.__list__.slice(start, end).map((localId) => this.__store__.get(localId));
    }
    /**
     * @param {number} [start]
     * @param {number} [deleteCount]
     * @param {...R} [newRecords]
     */
    splice(start, deleteCount, ...newRecords) {
        const oldRecords = this.slice(start, start + deleteCount);
        this.__list__.splice(start, deleteCount, ...newRecords.map((r) => r.localId));
        for (const r of oldRecords) {
            this.__deleteInverse__(r);
        }
        for (const r of newRecords) {
            this.__addInverse__(r);
        }
    }
    /** @param {Function} func */
    sort(func) {
        this.__list__.sort((a, b) => func(this.__store__.get(a), this.__store__.get(b)));
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        return this.__list__
            .map((localId) => this.__store__.get(localId))
            .concat(...collections.map((c) => [...c]));
    }
    *[Symbol.iterator]() {
        for (const localId of this.__list__) {
            yield this.__store__.get(localId);
        }
    }
}

/**
 * @template {Record} R
 * @augments RecordCollection
 */
export class RecordSet extends Set {
    constructor() {
        super();
        return new Proxy(this, {
            get(target, name, receiver) {
                if (name === "size") {
                    return receiver.__set__.size;
                }
                return Reflect.get(target, name, receiver);
            },
        });
    }

    /** @type {Set<string>} */
    __set__ = new Set();
    /** @param {R} r3 */
    add(r3) {
        this.__set__.add(r3?.localId);
        if (r3) {
            this.__addInverse__(r3);
        }
    }
    /** @param {R} r2 */
    delete(r2) {
        this.__set__.delete(r2?.localId);
        if (r2) {
            this.__deleteInverse__(r2);
        }
    }
    clear() {
        for (const r of this) {
            this.__deleteInverse__(r);
        }
        this.__set__.clear();
    }
    /** @param {R} record */
    has(record) {
        return this.__set__.has(record?.localId);
    }
    *values() {
        for (const localId of this.__set__) {
            yield this.__store__.get(localId);
        }
    }
    *keys() {
        for (const localId of this.__set__) {
            yield this.__store__.get(localId);
        }
    }
    *[Symbol.iterator]() {
        for (const localId of this.__set__) {
            yield this.__store__.get(localId);
        }
    }
}

class RecordCollection {
    /** @type {Record} */
    owner;
    /** @type {string} */
    name;
    /** @type {import("@mail/core/common/store_service").Store} */
    __store__;
    /** @param {Record} r3 */
    __addInverse__(r3) {
        r3.__invs__.add(this.owner.localId, this.name);
    }
    /** @param {Record} r2 */
    __deleteInverse__(r2) {
        r2.__invs__.delete(this.owner.localId, this.name);
    }
}

delete RecordCollection.prototype.constructor;
const RecordCollectionMixin = Object.fromEntries(
    Object.getOwnPropertyNames(RecordCollection.prototype).map((name) => [
        name,
        RecordCollection.prototype[name],
    ])
);
Object.assign(RecordList.prototype, RecordCollectionMixin);
Object.assign(RecordSet.prototype, RecordCollectionMixin);

export class Record {
    static id;
    /** @type {Object<string, Record>} */
    static records = {};
    /** @type {import("@mail/core/common/store_service").Store} */
    static store;
    /**
     * Contains tracked relational fields of the model. Value determines
     *
     * @type {Map<string, any>}
     */
    static __rels__ = new Map();
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
        let idStr;
        if (typeof data === "object" && data !== null) {
            idStr = this._localId(this.id, data);
        } else {
            idStr = data; // non-object data => single id
        }
        return `${this.name},${idStr}`;
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
        let res = vals.join(expr[0] === OR_SYM ? " OR " : " AND ");
        if (brackets) {
            res = `(${res})`;
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
     * @template {keyof import("model ").Models} M
     * @param {M} modelName
     * @returns {import("models").Models[M]}
     */
    static one(modelName) {
        return ONE_SYM;
    }
    /**
     * @template {keyof import("model").Models} M
     * @param {M} modelName
     * @returns {import("models").Collection<import("models").Models[M]>["List"]}
     */
    static List(modelName) {
        return MANY_LIST_SYM;
    }
    /**
     * @template {keyof import("model").Models} M
     * @param {M} modelName
     * @returns {import("models").Collection<import("models").Models[M]>["Set"]}
     */
    static Set(modelName) {
        return MANY_SET_SYM;
    }
    /**
     * @param {Object} data
     * @returns {Record}
     */
    static insert(data) {}

    /**
     * Raw relational values of the record, each of which contains object id(s)
     * rather than the record(s). This allows data in store and models being normalized,
     * which eases handling relations notably in when a record gets deleted.
     *
     * @type {Map<string, string|RecordList|RecordSet>}
     */
    __rels__ = new Map();
    /** Track inverse relations of current record. */
    __invs__ = new RecordInverses();
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
    /** @type {string} */
    localId;

    delete() {
        const r1 = this;
        for (const [name, l1] of r1.__rels__.entries()) {
            if (l1 instanceof RecordList) {
                r1[name] = [];
            } else if (l1 instanceof RecordSet) {
                r1[name].clear();
            } else {
                r1[name] = undefined;
            }
        }
        for (const [localId, names] of r1.__invs__.__map__.entries()) {
            for (const [name2, count] of names.entries()) {
                const r2 = this._store.get(localId);
                const l2 = r2.__rels__.get(name2);
                if (l2 instanceof RecordList) {
                    for (let c = 0; c < count; c++) {
                        const index = r2[name2].findIndex((i) => i.eq(r1));
                        r2[name2].splice(index, 1);
                    }
                } else if (l2 instanceof RecordSet) {
                    r2[name2].delete(r1);
                } else {
                    r2[name2] = undefined;
                }
            }
        }
        delete this.Model?.records[r1.localId];
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

    /** @param {Record[]|RecordList|RecordSet} collection */
    in(collection) {
        if (!collection) {
            return false;
        }
        if (collection instanceof RecordList) {
            return collection.includes(this);
        }
        if (collection instanceof RecordSet) {
            return collection.has(this);
        }
        // Array
        return collection.some((record) => record.eq(this));
    }

    /** @param {Record[]|RecordList|RecordSet} collection */
    notIn(collection) {
        return !this.in(collection);
    }
}

Record.register();
