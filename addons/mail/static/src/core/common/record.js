/* @odoo-module */

import { toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

const MANY_SYM = Symbol("many");
const ONE_SYM = Symbol("one");
const OR_SYM = Symbol("or");
const AND_SYM = Symbol("and");
const IS_RECORD_SYM = Symbol("isRecord");

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
 */
export class RecordList extends Array {
    static isOne(list) {
        return Boolean(list[ONE_SYM]);
    }
    static isMany(list) {
        return Boolean(list[MANY_SYM]);
    }
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

    /** @param {ONE_SYM|MANY_SYM} SYM */
    constructor(SYM) {
        super();
        this[SYM] = true;
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
                    receiver._insert(val, (r3) => {
                        const r2 = receiver[index];
                        if (r2 && r2.notEq(r3)) {
                            receiver.__deleteInverse__(r2);
                        }
                        const { inverse, onDelete } = receiver.owner.Model.__rels__.get(
                            receiver.name
                        );
                        onDelete?.call(receiver.owner, r2);
                        if (inverse) {
                            r2.__rels__.get(inverse).delete(receiver);
                        }
                        receiver.__list__[index] = r3?.localId;
                        if (r3) {
                            receiver.__addInverse__(r3);
                            const { inverse, onAdd } = receiver.owner.Model.__rels__.get(
                                receiver.name
                            );
                            onAdd?.call(receiver.owner, r3);
                            if (inverse) {
                                r3.__rels__.get(inverse).add(receiver);
                            }
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
     * @param {(R) => void} fn function that is called in-between preinsert and
     *   insert. Preinsert only inserted what's needed to make record, while
     *   insert finalize with all remaining data.
     * @param {boolean} [inv=true] whether the inverse should be added or not.
     *   It is always added except when during an insert on a relational field,
     *   in order to avoid infinite loop.
     * @param {"ADD"|"DELETE} [mode="ADD"] the mode of insert on the relation.
     *   Important to match the inverse. Most of the time it's "ADD", that is when
     *   inserting the relation the inverse should be added. Exception when the insert
     *   comes from deletion, we want to "DELETE".
     */
    _insert(val, fn, { inv = true, mode = "ADD" } = {}) {
        const { inverse } = this.owner.Model.__rels__.get(this.name);
        if (inverse && inv) {
            // special command to call __addNoinv/__deleteNoInv, to prevent infinite loop
            val[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", this.owner]];
        }
        /** @type {R} */
        let r3;
        if (!Record.isRecord(val)) {
            const { targetModel } = this.owner.Model.__rels__.get(this.name);
            r3 = this.owner.Model.store[targetModel].preinsert(val);
        } else {
            r3 = val;
        }
        fn(r3);
        if (!Record.isRecord(val)) {
            // was preinserted, fully insert now
            const { targetModel } = this.owner.Model.__rels__.get(this.name);
            this.owner.Model.store[targetModel].insert(val);
        }
        return r3;
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
            const r = this._insert(val, (r3) => {
                this.__list__.push(r3.localId);
                this.__addInverse__(r3);
            });
            const { inverse, onAdd } = this.owner.Model.__rels__.get(this.name);
            onAdd?.call(this.owner, r);
            if (inverse) {
                r.__rels__.get(inverse).add(this.owner);
            }
        }
        return this.__list__.length;
    }
    /** @returns {R} */
    pop() {
        const r2 = this.at(-1);
        if (r2) {
            this.splice(this.length - 1, 1);
        }
        return r2;
    }
    /** @returns {R} */
    shift() {
        const r2 = this.__store__.get(this.__list__.shift());
        if (r2) {
            this.__deleteInverse__(r2);
        }
        const { inverse, onDelete } = this.owner.Model.__rels__.get(this.name);
        if (r2) {
            onDelete?.call(this.owner, r2);
            if (inverse) {
                r2.__rels__.get(inverse).delete(this.owner);
            }
        }
        return r2;
    }
    /** @param {R[]} records */
    unshift(...records) {
        for (const val of records) {
            const r = this._insert(val, (r3) => {
                this.__list__.unshift(r3.localId);
                this.__addInverse__(r3);
            });
            const { inverse, onAdd } = this.owner.Model.__rels__.get(this.name);
            onAdd?.call(this.owner, r);
            if (inverse) {
                r.__rels__.get(inverse).add(this.owner);
            }
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
            const { inverse, onDelete } = this.owner.Model.__rels__.get(this.name);
            onDelete?.call(this.owner, r);
            if (inverse) {
                r.__rels__.get(inverse).delete(this.owner);
            }
        }
        for (const r of newRecords) {
            this.__addInverse__(r);
            const { inverse, onAdd } = this.owner.Model.__rels__.get(this.name);
            onAdd?.call(this.owner, r);
            if (inverse) {
                r.__rels__.get(inverse).add(this.owner);
            }
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
        if (RecordList.isOne(this)) {
            const last = records.at(-1);
            if (Record.isRecord(last) && last.in(this)) {
                return;
            }
            this._insert(last, (r) => {
                if (r.notEq(this[0])) {
                    this.pop();
                    this.push(r);
                }
            });
            return;
        }
        for (const val of records) {
            if (Record.isRecord(val) && val.in(this)) {
                continue;
            }
            this._insert(val, (r) => {
                if (this.indexOf(r) === -1) {
                    this.push(r);
                }
            });
        }
    }
    /**
     * Version of add() that does not update the inverse.
     * This is internally called when inserting (with intent to add)
     * on relational field with inverse, to prevent infinite loops.
     *
     * @param {...R}
     */
    __addNoinv(...records) {
        if (RecordList.isOne(this)) {
            const last = records.at(-1);
            if (Record.isRecord(last) && last.in(this)) {
                return;
            }
            this._insert(
                last,
                (r) => {
                    if (r.notEq(this[0])) {
                        const old = this.__list__.pop();
                        if (old) {
                            this.__deleteInverse__(old);
                        }
                        this.__list__.push(r.localId);
                        this.__addInverse__(r);
                    }
                },
                { inv: false }
            );
            return;
        }
        for (const val of records) {
            if (Record.isRecord(val) && val.in(this)) {
                continue;
            }
            this._insert(
                val,
                (r) => {
                    if (this.indexOf(r) === -1) {
                        this.__list__.push(r.localId);
                        this.__addInverse__(r);
                    }
                },
                { inv: false }
            );
        }
    }
    /** @param {...R}  */
    delete(...records) {
        for (const val of records) {
            this._insert(
                val,
                (r) => {
                    const index = this.indexOf(r);
                    if (index !== -1) {
                        this.splice(index, 1);
                    }
                },
                { mode: "DELETE" }
            );
        }
    }
    /**
     * Version of delete() that does not update the inverse.
     * This is internally called when inserting (with intent to delete)
     * on relational field with inverse, to prevent infinite loops.
     *
     * @param {...R}
     */
    __deleteNoinv(...records) {
        for (const val of records) {
            this._insert(
                val,
                (r) => {
                    const index = this.indexOf(r);
                    if (index !== -1) {
                        this.__list__.splice(index, 1);
                        this.__deleteInverse__(r);
                    }
                },
                { inv: false }
            );
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
    static isRecord(record) {
        return Boolean(record?.[IS_RECORD_SYM]);
    }
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
                if (RecordList.isMany(this.__rels__.get(expr))) {
                    throw new Error("Using a Record.Many() as id is not (yet) supported");
                }
                if (this.isCommand(data[expr])) {
                    // Note: only Record.one() is supported
                    const [cmd, data2] = data[expr].at(-1);
                    if (cmd === "DELETE") {
                        return undefined;
                    } else {
                        return `(${data2?.localId})`;
                    }
                }
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
                if (Record.isCommand(data[expr2])) {
                    // Note: only Record.one() is supported
                    const [cmd, data2] = data[expr2].at(-1);
                    return Object.assign(res, {
                        [expr2]:
                            cmd === "DELETE"
                                ? undefined
                                : cmd === "DELETE.noinv"
                                ? [["DELETE.noinv", data2]]
                                : cmd === "ADD.noinv"
                                ? [["ADD.noinv", data2]]
                                : data2,
                    });
                }
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
            if (Record.isCommand(data[this.id])) {
                // Note: only Record.one() is supported
                const [cmd, data2] = data[this.id].at(-1);
                if (cmd === "DELETE") {
                    return { [this.id]: undefined };
                } else {
                    return { [this.id]: data2 };
                }
            }
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
        let record = Object.assign(obj, {
            [IS_RECORD_SYM]: true,
            Model: this,
            localId: this.localId(data),
            ...ids,
        });
        Object.assign(record, { _store: this.store });
        this.records[record.localId] = record;
        // return reactive version
        record = this.records[record.localId];
        return record;
    }
    /**
     * @template {keyof import("model ").Models} M
     * @param {M} targetModel
     * @param {string} [inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(r: M) => void} [onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(r: M) => void} [onDelete] function that is called when a record is removed
     *   from the relation.
     * @returns {import("models").Models[M]}
     */
    static one(targetModel, { inverse, onAdd, onDelete } = {}) {
        return [ONE_SYM, { targetModel, inverse, onAdd, onDelete }];
    }
    /**
     * @template {keyof import("model").Models} M
     * @param {M} targetModel
     * @param {string} [inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(r: M) => void} [onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(r: M) => void} [onDelete] function that is called when a record is removed
     *   from the relation.
     * @returns {import("models").Models[M][]}
     */
    static many(targetModel, { inverse, onAdd, onDelete } = {}) {
        return [MANY_SYM, { targetModel, inverse, onAdd, onDelete }];
    }
    /** @returns {Record} */
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
    static isCommand(data) {
        return ["ADD", "DELETE", "ADD.noinv", "DELETE.noinv"].includes(data?.[0]?.[0]);
    }

    /**
     * Raw relational values of the record, each of which contains object id(s)
     * rather than the record(s). This allows data in store and models being normalized,
     * which eases handling relations notably in when a record gets deleted.
     *
     * @type {Map<string, RecordList>}
     */
    __rels__ = new Map();
    /** @type {Map<string, { targetModel: string }>} */
    __invs__ = new RecordInverses();
    get _store() {
        return this.Model.store;
    }
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

    update(data) {
        Object.assign(this, data);
    }

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
                if (RecordList.isMany(l2)) {
                    for (let c = 0; c < count; c++) {
                        r2[name2].delete(r1);
                    }
                } else {
                    r2[name2] = undefined;
                }
            }
        }
        delete this.Model.records[r1.localId];
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

    toData() {
        const data = { ...this };
        for (const [name, val] of this.__rels__.entries()) {
            if (RecordList.isMany(val)) {
                data[name] = val.map((r) => r.toIdData());
            } else {
                data[name] = this[name]?.toIdData();
            }
        }
        delete data._store;
        delete data.__rels__;
        delete data.__invs__;
        delete data.Model;
        return data;
    }
    toIdData() {
        const data = this.constructor._retrieveIdFromData(this);
        for (const [name, val] of Object.entries(data)) {
            if (Record.isRecord(val)) {
                data[name] = val.toIdData();
            }
        }
        return data;
    }
}

Record.register();
