/* @odoo-module */

import { toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

const MANY_SYM = Symbol("many");
const ONE_SYM = Symbol("one");
const OR_SYM = Symbol("or");
const AND_SYM = Symbol("and");

export function AND(...args) {
    return [AND_SYM, ...args];
}
export function OR(...args) {
    return [OR_SYM, ...args];
}

/**
 * @param {R|any} val
 * @param {Record} record
 * @param {string} fname
 * @param {(R) => void} fn
 */
export function preinsert(val, record, fname, fn) {
    /** @type {R} */
    let r3;
    if (!(val instanceof Record)) {
        const { targetModel } = record.Model.__rels__.get(fname);
        r3 = record.Model.store[targetModel].preinsert(val);
    } else {
        r3 = val;
    }
    fn(r3);
    if (!(val instanceof Record)) {
        // was preinserted, fully insert now
        const { targetModel } = record.Model.__rels__.get(fname);
        record.Model.store[targetModel].insert(val);
    }
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
 */
export class RecordList extends Array {
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

    /** @type {string[]} */
    __list__ = [];

    constructor() {
        super();
        return new Proxy(this, {
            /** @param {RecordList<R>} receiver */
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
            /** @param {RecordList<R>} receiver */
            set(target, name, val, receiver) {
                if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                    // support for "array[index] = r3" syntax
                    const index = parseInt(name);
                    receiver._preinsert(val, (r3) => {
                        const r2 = receiver[index];
                        if (r2 && r2.notEq(r3)) {
                            receiver.__deleteInverse__(r2);
                        }
                        receiver.__list__[index] = r3?.localId;
                        if (r3) {
                            receiver.__addInverse__(r3);
                        }
                    });
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
    /**
     * @param {R|any} val
     * @param {(R) => void} fn
     */
    _preinsert(val, fn) {
        preinsert(val, this.owner, this.name, fn);
    }
    /**
     * @param {number} index
     * @returns {R}
     */
    at(index) {
        return this.__store__.get(this.__list__.at(index));
    }
    /** @param {R[]} records */
    push(...records) {
        for (const val of records) {
            this._preinsert(val, (r3) => {
                this.__list__.push(r3.localId);
                this.__addInverse__(r3);
            });
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
        for (const val of records) {
            this._preinsert(val, (r3) => {
                this.__list__.unshift(r3.localId);
                this.__addInverse__(r3);
            });
        }
        return this.__list__.length;
    }
    /**
     * @param {(a: R, b: R) => boolean} func
     * @returns {R[]}
     */
    map(func) {
        return this.__list__.map((localId) => func(this.__store__.get(localId)));
    }
    /**
     * @param {(a: R, b: R) => boolean} predicate
     * @returns {R[]}
     */
    filter(predicate) {
        return this.__list__
            .filter((localId) => predicate(this.__store__.get(localId)))
            .map((localId) => this.__store__.get(localId));
    }
    /** @param {(a: R, b: R) => boolean} predicate */
    some(predicate) {
        return this.__list__.some((localId) => predicate(this.__store__.get(localId)));
    }
    /** @param {(a: R, b: R) => boolean} predicate */
    every(predicate) {
        return this.__list__.every((localId) => predicate(this.__store__.get(localId)));
    }
    /**
     * @param {(a: R, b: R) => boolean} predicate
     * @returns {R}
     */
    find(predicate) {
        return this.__store__.get(
            this.__list__.find((localId) => predicate(this.__store__.get(localId)))
        );
    }
    /** @param {(a: R, b: R) => boolean} predicate */
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
    /** @param {(acc: any, r: R) => any} fn */
    reduce(fn, init) {
        return this.__list__.reduce((acc, localId) => fn(acc, this.__store__.get(localId)), init);
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
    /** @param {(a: R, b: R) => boolean} func */
    sort(func) {
        this.__list__.sort((a, b) => func(this.__store__.get(a), this.__store__.get(b)));
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        return this.__list__
            .map((localId) => this.__store__.get(localId))
            .concat(...collections.map((c) => [...c]));
    }
    /** @param {...R}  */
    add(...records) {
        for (const val of records) {
            this._preinsert(val, (r) => {
                if (this.indexOf(r) === -1) {
                    this.push(r);
                }
            });
        }
    }
    /** @param {...R}  */
    delete(...records) {
        for (const val of records) {
            this._preinsert(val, (r) => {
                const index = this.indexOf(r);
                if (index !== -1) {
                    this.splice(index, 1);
                }
            });
        }
    }
    clear() {
        while (this.__list__.length > 0) {
            this.pop();
        }
    }
    /** @yields {R} */
    *[Symbol.iterator]() {
        for (const localId of this.__list__) {
            yield this.__store__.get(localId);
        }
    }
}

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
            if (this.__rels__.has(expr)) {
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
    static _retrieveIdFromData(data) {
        const res = {};
        function _deepRetrieve(expr2) {
            if (typeof expr2 === "string") {
                return Object.assign(res, { [expr2]: data[expr2] });
            }
            if (expr2 instanceof Array) {
                for (const expr of this.id) {
                    if (typeof expr === "symbol") {
                        continue;
                    }
                    _deepRetrieve(expr);
                }
            }
        }
        if (this.id === undefined) {
            return res;
        }
        if (typeof this.id === "string") {
            return { [this.id]: data[this.id] };
        }
        for (const expr of this.id) {
            if (typeof expr === "symbol") {
                continue;
            }
            _deepRetrieve(expr);
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
        const ids = this._retrieveIdFromData(data);
        let record = Object.assign(obj, { Model: this, localId: this.localId(data), ...ids });
        Object.assign(record, { _store: this.store });
        this.records[record.localId] = record;
        // return reactive version
        record = this.records[record.localId];
        return record;
    }
    /**
     * @template {keyof import("model ").Models} M
     * @param {M} modelName
     * @returns {import("models").Models[M]}
     */
    static one(modelName) {
        return [ONE_SYM, modelName];
    }
    /**
     * @template {keyof import("model").Models} M
     * @param {M} modelName
     * @returns {import("models").Models[M][]}
     */
    static many(modelName) {
        return [MANY_SYM, modelName];
    }
    /**
     * @param {Object} data
     * @returns {Record}
     */
    static insert(data) {
        const res = this.preinsert(data);
        res.update(data);
        return res;
    }
    /**
     * @param {Object} data
     * @returns {Record}
     */
    static preinsert(data) {
        return this.get(data) ?? this.new(data);
    }

    /**
     * Raw relational values of the record, each of which contains object id(s)
     * rather than the record(s). This allows data in store and models being normalized,
     * which eases handling relations notably in when a record gets deleted.
     *
     * @type {Map<string, string|RecordList>}
     */
    __rels__ = new Map();
    /** @type {Map<string, { targetModel: string }>} */
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

    constructor() {
        this.setup();
    }

    setup() {}

    update(data) {}

    delete() {
        const r1 = this;
        for (const name of r1.__rels__.keys()) {
            r1[name] = undefined;
        }
        for (const [localId, names] of r1.__invs__.__map__.entries()) {
            for (const [name2, count] of names.entries()) {
                const r2 = this._store.get(localId);
                if (!r2) {
                    // record already deleted, clean inverses
                    r1.__invs__.__map__.delete(localId);
                    continue;
                }
                const l2 = r2.__rels__.get(name2);
                if (l2 instanceof RecordList) {
                    for (let c = 0; c < count; c++) {
                        r2[name2].delete(r1);
                    }
                } else {
                    r2[name2] = undefined;
                }
            }
        }
        if (this.Model) {
            delete this.Model.records[r1.localId];
            delete this.Model;
        }
    }

    /** @param {Record} record */
    eq(record) {
        return toRaw(this) === toRaw(record);
    }

    /** @param {Record} record */
    notEq(record) {
        return !this.eq(record);
    }

    /** @param {Record[]|RecordList} collection */
    in(collection) {
        if (!collection) {
            return false;
        }
        if (collection instanceof RecordList) {
            return collection.includes(this);
        }
        // Array
        return collection.some((record) => record.eq(this));
    }

    /** @param {Record[]|RecordList} collection */
    notIn(collection) {
        return !this.in(collection);
    }
}

Record.register();
