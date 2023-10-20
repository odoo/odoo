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

export class RecordUses {
    /**
     * Track the uses of a record. Each record contains a single `RecordUses`:
     * - Key: localId of record that uses current record
     * - Value: Map where key is relational field name, and value is number
     *          of time current record is present in this relation.
     *
     * @type {Map<string, Map<string, number>>}}
     */
    data = new Map();
    /** @param {RecordList} list */
    add(list) {
        if (!this.data.has(list.owner.localId)) {
            this.data.set(list.owner.localId, new Map());
        }
        const use = this.data.get(list.owner.localId);
        if (!use.get(list.name)) {
            use.set(list.name, 0);
        }
        use.set(list.name, use.get(list.name) + 1);
    }
    /** @param {RecordList} list */
    delete(list) {
        if (!this.data.has(list.owner.localId)) {
            return;
        }
        const use = this.data.get(list.owner.localId);
        if (!use.get(list.name)) {
            return;
        }
        use.set(list.name, use.get(list.name) - 1);
        if (use.get(list.name) === 0) {
            use.delete(list.name);
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
    /** @type {import("models").Store} */
    store;
    /** @type {string[]} */
    data = [];

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
                    return receiver.store.get(receiver.data[index]);
                }
                if (name === "length") {
                    return receiver.data.length;
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
                            r2.__uses__.delete(receiver);
                        }
                        const { inverse, onDelete } = receiver.owner.Model.__rels__[receiver.name];
                        onDelete?.call(receiver.owner, r2);
                        if (inverse) {
                            r2.__rels__[inverse].delete(receiver);
                        }
                        receiver.data[index] = r3?.localId;
                        if (r3) {
                            r3.__uses__.add(receiver);
                            const { inverse, onAdd } = receiver.owner.Model.__rels__[receiver.name];
                            onAdd?.call(receiver.owner, r3);
                            if (inverse) {
                                r3.__rels__[inverse].add(receiver);
                            }
                        }
                    });
                } else if (name === "length") {
                    const newLength = parseInt(val);
                    if (newLength < receiver.length) {
                        receiver.splice(newLength, receiver.length - newLength);
                    }
                    receiver.data.length = newLength;
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
        const { inverse } = this.owner.Model.__rels__[this.name];
        if (inverse && inv) {
            // special command to call _addNoinv/_deleteNoInv, to prevent infinite loop
            val[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", this.owner]];
        }
        /** @type {R} */
        let r3;
        if (!Record.isRecord(val)) {
            const { targetModel } = this.owner.Model.__rels__[this.name];
            r3 = this.owner.Model.store[targetModel].preinsert(val);
        } else {
            r3 = val;
        }
        fn(r3);
        if (!Record.isRecord(val)) {
            // was preinserted, fully insert now
            const { targetModel } = this.owner.Model.__rels__[this.name];
            this.owner.Model.store[targetModel].insert(val);
        }
        return r3;
    }
    /**
     * @param {number} index
     * @returns {R}
     */
    at(index) {
        return this.store.get(this.data.at(index));
    }
    /** @param {R[]} records */
    push(...records) {
        for (const val of records) {
            const r = this._insert(val, (r3) => {
                this.data.push(r3.localId);
                r3.__uses__.add(this);
            });
            const { inverse, onAdd } = this.owner.Model.__rels__[this.name];
            onAdd?.call(this.owner, r);
            if (inverse) {
                r.__rels__[inverse].add(this.owner);
            }
        }
        return this.data.length;
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
        const r2 = this.store.get(this.data.shift());
        r2?.__uses__.delete(this);
        const { inverse, onDelete } = this.owner.Model.__rels__[this.name];
        if (r2) {
            onDelete?.call(this.owner, r2);
            if (inverse) {
                r2.__rels__[inverse].delete(this.owner);
            }
        }
        return r2;
    }
    /** @param {R[]} records */
    unshift(...records) {
        for (const val of records) {
            const r = this._insert(val, (r3) => {
                this.data.unshift(r3.localId);
                r3.__uses__.add(this);
            });
            const { inverse, onAdd } = this.owner.Model.__rels__[this.name];
            onAdd?.call(this.owner, r);
            if (inverse) {
                r.__rels__[inverse].add(this.owner);
            }
        }
        return this.data.length;
    }
    /**
     * @param {(a: R, b: R) => boolean} func
     * @returns {R[]}
     */
    map(func) {
        return this.data.map((localId) => func(this.store.get(localId)));
    }
    /**
     * @param {(a: R, b: R) => boolean} predicate
     * @returns {R[]}
     */
    filter(predicate) {
        return this.data
            .filter((localId) => predicate(this.store.get(localId)))
            .map((localId) => this.store.get(localId));
    }
    /** @param {(a: R, b: R) => boolean} predicate */
    some(predicate) {
        return this.data.some((localId) => predicate(this.store.get(localId)));
    }
    /** @param {(a: R, b: R) => boolean} predicate */
    every(predicate) {
        return this.data.every((localId) => predicate(this.store.get(localId)));
    }
    /**
     * @param {(a: R, b: R) => boolean} predicate
     * @returns {R}
     */
    find(predicate) {
        return this.store.get(this.data.find((localId) => predicate(this.store.get(localId))));
    }
    /** @param {(a: R, b: R) => boolean} predicate */
    findIndex(predicate) {
        return this.data.findIndex((localId) => predicate(this.store.get(localId)));
    }
    /** @param {R} record */
    indexOf(record) {
        return this.data.indexOf(record?.localId);
    }
    /** @param {R} record */
    includes(record) {
        return this.data.includes(record.localId);
    }
    /** @param {(acc: any, r: R) => any} fn */
    reduce(fn, init) {
        return this.data.reduce((acc, localId) => fn(acc, this.store.get(localId)), init);
    }
    /**
     * @param {number} [start]
     * @param {number} [end]
     * @returns {R[]}
     */
    slice(start, end) {
        return this.data.slice(start, end).map((localId) => this.store.get(localId));
    }
    /**
     * @param {number} [start]
     * @param {number} [deleteCount]
     * @param {...R} [newRecords]
     */
    splice(start, deleteCount, ...newRecords) {
        const oldRecords = this.slice(start, start + deleteCount);
        this.data.splice(start, deleteCount, ...newRecords.map((r) => r.localId));
        for (const r of oldRecords) {
            r.__uses__.delete(this);
            const { inverse, onDelete } = this.owner.Model.__rels__[this.name];
            onDelete?.call(this.owner, r);
            if (inverse) {
                r.__rels__[inverse].delete(this.owner);
            }
        }
        for (const r of newRecords) {
            r.__uses__.add(this);
            const { inverse, onAdd } = this.owner.Model.__rels__[this.name];
            onAdd?.call(this.owner, r);
            if (inverse) {
                r.__rels__[inverse].add(this.owner);
            }
        }
    }
    /** @param {(a: R, b: R) => boolean} func */
    sort(func) {
        const list = this.data.slice(); // sort on copy of list so that reactive observers not triggered while sorting
        list.sort((a, b) => func(this.store.get(a), this.store.get(b)));
        this.data = list;
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        return this.data
            .map((localId) => this.store.get(localId))
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
    _addNoinv(...records) {
        if (RecordList.isOne(this)) {
            const last = records.at(-1);
            if (Record.isRecord(last) && last.in(this)) {
                return;
            }
            this._insert(
                last,
                (r) => {
                    if (r.notEq(this[0])) {
                        const old = this.at(-1);
                        this.data.pop();
                        old?.__uses__.delete(this);
                        this.data.push(r.localId);
                        r.__uses__.add(this);
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
                        this.data.push(r.localId);
                        r.__uses__.add(this);
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
    _deleteNoinv(...records) {
        for (const val of records) {
            this._insert(
                val,
                (r) => {
                    const index = this.indexOf(r);
                    if (index !== -1) {
                        this.data.splice(index, 1);
                        r.__uses__.delete(this);
                    }
                },
                { inv: false }
            );
        }
    }
    clear() {
        while (this.data.length > 0) {
            this.pop();
        }
    }
    /** @yields {R} */
    *[Symbol.iterator]() {
        for (const localId of this.data) {
            yield this.store.get(localId);
        }
    }
}

/**
 * @typedef {Object} RelationDefinition
 * @property {string} [targetModel]
 * @property {Function} [compute]
 * @property {string} [inverse]
 * @property {Function} [onAdd]
 * @property {Function} [onDelete]
 */

export class Record {
    static id;
    /** @type {Object<string, Record>} */
    static records = {};
    /** @type {import("@mail/core/common/store_service").Store} */
    static store;
    /**
     * Contains tracked relational fields of the model:
     * - key : (relational) field name
     * - value: Value contains definition of relational field
     *
     * @type {Object.<string, {RelationDefinition}>}
     */
    static __rels__ = {};
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
            if (expr in this.__rels__) {
                if (RecordList.isMany(this.__rels__[expr])) {
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
            if (typeof data !== "object" || data === null) {
                return { [this.id]: data }; // non-object data => single id
            }
            if (Record.isCommand(data[this.id])) {
                // Note: only Record.one() is supported
                const [cmd, data2] = data[this.id].at(-1);
                return Object.assign(res, {
                    [this.id]:
                        cmd === "DELETE"
                            ? undefined
                            : cmd === "DELETE.noinv"
                            ? [["DELETE.noinv", data2]]
                            : cmd === "ADD.noinv"
                            ? [["ADD.noinv", data2]]
                            : data2,
                });
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
        for (const compute of Object.values(record.__computes__)) {
            compute();
        }
        Object.assign(record, { _store: this.store });
        this.records[record.localId] = record;
        // return reactive version
        record = this.records[record.localId];
        return record;
    }
    /**
     * @template {keyof import("models").Models} M
     * @param {M} targetModel
     * @param {Function} [compute] if set, the value of this relational field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @param {string} [inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(r: M) => void} [onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(r: M) => void} [onDelete] function that is called when a record is removed
     *   from the relation.
     * @returns {import("models").Models[M]}
     */
    static one(targetModel, { compute, inverse, onAdd, onDelete } = {}) {
        return [ONE_SYM, { targetModel, compute, inverse, onAdd, onDelete }];
    }
    /**
     * @template {keyof import("models").Models} M
     * @param {M} targetModel
     * @param {Function} [compute] if set, the value of this relational field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @param {string} [inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(r: M) => void} [onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(r: M) => void} [onDelete] function that is called when a record is removed
     *   from the relation.
     * @returns {import("models").Models[M][]}
     */
    static many(targetModel, { compute, inverse, onAdd, onDelete } = {}) {
        return [MANY_SYM, { targetModel, compute, inverse, onAdd, onDelete }];
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
     * Object that contains compute functions of computed fields, i.e. fields that have have
     * a compute method. @see compute param in Record.one and Record.many. Key is field name
     * and value is function. The function is the one from the definition. It is not bounded
     * to the record nor its invoke does assign the value on the targeted field. See non-static
     * __computes__ for bounded function whose call auto re-assign value on the field.
     *
     * @type {Object<string, Function>}
     */
    static __computes__ = {};

    /**
     * Object that contains bounded compute functions of computed fields. Equivalent to
     * static `__computes__` but the functions are bounded to the current record, and
     * invoking the function does automatically re-assign new value on the computed
     * field.
     *
     * @type {Object<string, Function>}
     */
    __computes__ = {};
    /**
     * Raw relational values of the record, each of which contains object id(s)
     * rather than the record(s). This allows data in store and models being normalized,
     * which eases handling relations notably in when a record gets deleted.
     *
     * @type {Object<string, RecordList>}
     */
    __rels__ = {};
    __uses__ = new RecordUses();
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
        if (typeof data === "object" && data !== null) {
            Object.assign(this, data);
        } else {
            // update on single-id data
            if (this.Model.id in this.Model.__rels__) {
                this[this.Model.id] = data;
            }
        }
    }

    delete() {
        const r1 = this;
        for (const name in r1.__rels__) {
            r1[name] = undefined;
        }
        for (const [localId, names] of r1.__uses__.data.entries()) {
            for (const [name2, count] of names.entries()) {
                const r2 = this._store.get(localId);
                if (!r2) {
                    // record already deleted, clean inverses
                    r1.__uses__.data.delete(localId);
                    continue;
                }
                const l2 = r2.__rels__[name2];
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
        for (const [name, val] of Object.entries(this.__rels__)) {
            if (RecordList.isMany(val)) {
                data[name] = val.map((r) => r.toIdData());
            } else {
                data[name] = this[name]?.toIdData();
            }
        }
        delete data._store;
        delete data.__rels__;
        delete data.__uses__;
        delete data.Model;
        return data;
    }
    toIdData() {
        const data = this.Model._retrieveIdFromData(this);
        for (const [name, val] of Object.entries(data)) {
            if (Record.isRecord(val)) {
                data[name] = val.toIdData();
            }
        }
        return data;
    }
}

Record.register();
