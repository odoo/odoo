/* @odoo-module */

import { toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

const ATTR_SYM = Symbol("attr");
const MANY_SYM = Symbol("many");
const ONE_SYM = Symbol("one");
const OR_SYM = Symbol("or");
const AND_SYM = Symbol("and");
const IS_RECORD_SYM = Symbol("isRecord");

/** @typedef {ATTR_SYM|MANY_SYM|ONE_SYM} FIELD_SYM */

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
                if (
                    typeof name === "symbol" ||
                    Object.keys(target).includes(name) ||
                    Object.prototype.hasOwnProperty.call(target.constructor.prototype, name)
                ) {
                    return Reflect.get(target, name, receiver);
                } else {
                    // Attempt an unimplemented array method call
                    const array = [...receiver];
                    return array[name].bind(array);
                }
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
                        const { inverse, onDelete } = receiver.owner.Model._fields[receiver.name];
                        onDelete?.call(receiver.owner, r2);
                        if (inverse) {
                            r2._fields[inverse].delete(receiver);
                        }
                        receiver.data[index] = r3?.localId;
                        if (r3) {
                            r3.__uses__.add(receiver);
                            const { inverse, onAdd } = receiver.owner.Model._fields[receiver.name];
                            onAdd?.call(receiver.owner, r3);
                            if (inverse) {
                                r3._fields[inverse].add(receiver);
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
        const { inverse } = this.owner.Model._fields[this.name];
        if (inverse && inv) {
            // special command to call _addNoinv/_deleteNoInv, to prevent infinite loop
            val[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", this.owner]];
        }
        /** @type {R} */
        let r3;
        if (!Record.isRecord(val)) {
            const { targetModel } = this.owner.Model._fields[this.name];
            r3 = this.owner.Model.store[targetModel].preinsert(val);
        } else {
            r3 = val;
        }
        fn(r3);
        if (!Record.isRecord(val)) {
            // was preinserted, fully insert now
            const { targetModel } = this.owner.Model._fields[this.name];
            this.owner.Model.store[targetModel].insert(val);
        }
        return r3;
    }
    /** @param {R[]} records */
    push(...records) {
        for (const val of records) {
            const r = this._insert(val, (r3) => {
                this.data.push(r3.localId);
                r3.__uses__.add(this);
            });
            const { inverse, onAdd } = this.owner.Model._fields[this.name];
            onAdd?.call(this.owner, r);
            if (inverse) {
                r._fields[inverse].add(this.owner);
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
        const { inverse, onDelete } = this.owner.Model._fields[this.name];
        if (r2) {
            onDelete?.call(this.owner, r2);
            if (inverse) {
                r2._fields[inverse].delete(this.owner);
            }
        }
        return r2;
    }
    /** @param {R[]} records */
    unshift(...records) {
        for (let i = records.length - 1; i >= 0; i--) {
            const r = this._insert(records[i], (r3) => {
                this.data.unshift(r3.localId);
                r3.__uses__.add(this);
            });
            const { inverse, onAdd } = this.owner.Model._fields[this.name];
            onAdd?.call(this.owner, r);
            if (inverse) {
                r._fields[inverse].add(this.owner);
            }
        }
        return this.data.length;
    }
    /** @param {R} record */
    indexOf(record) {
        return this.data.indexOf(record?.localId);
    }
    /**
     * @param {number} [start]
     * @param {number} [deleteCount]
     * @param {...R} [newRecords]
     */
    splice(start, deleteCount, ...newRecords) {
        const oldRecords = this.slice(start, start + deleteCount);
        const list = this.data.slice(); // splice on copy of list so that reactive observers not triggered while splicing
        list.splice(start, deleteCount, ...newRecords.map((r) => r.localId));
        this.data = list;
        for (const r of oldRecords) {
            r.__uses__.delete(this);
            const { inverse, onDelete } = this.owner.Model._fields[this.name];
            onDelete?.call(this.owner, r);
            if (inverse) {
                r._fields[inverse].delete(this.owner);
            }
        }
        for (const r of newRecords) {
            r.__uses__.add(this);
            const { inverse, onAdd } = this.owner.Model._fields[this.name];
            onAdd?.call(this.owner, r);
            if (inverse) {
                r._fields[inverse].add(this.owner);
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
 * @typedef {Object} FieldDefinition
 * @property {boolean} [ATTR_SYM] true when this is an attribute, i.e. a non-relational field.
 * @property {boolean} [MANY_SYM] true when this is a many relation.
 * @property {boolean} [ONE_SYM] true when this is a one relation.
 * @property {any} [default] the default value of this attribute.
 * @property {boolean} [html] whether the attribute is an html field. Useful to automatically markup
 *   when the insert is trusted.
 * @property {string} [targetModel] model name of records contained in this relational field.
 * @property {Function} [compute] if set the field is computed based on provided function.
 *   The `this` of function is the record, and the function is recalled whenever any field
 *   in models used by this compute function is changed.
 * @property {string} [inverse] name of inverse relational field in targetModel.
 * @property {Function} [onAdd] hook that is called when relation is updated
 *   with a record being added. Callback param is record being added into relation.
 * @property {Function} [onDelete] hook that is called when relation is updated
 *   with a record being deleted. Callback param is record being deleted from relation.
 */

export class Record {
    /** @param {FieldDefinition} */
    static isAttr(definition) {
        return Boolean(definition[ATTR_SYM]);
    }
    /**
     * Determines whether the inserts are considered trusted or not.
     * Useful to auto-markup html fields when this is set
     */
    static trusted = false;
    static id;
    /** @type {Object<string, Record>} */
    static records = {};
    /** @type {import("@mail/core/common/store_service").Store} */
    static store;
    /**
     * Contains field definitions of the model:
     * - key : field name
     * - value: Value contains definition of field
     *
     * @type {Object.<string, FieldDefinition>}
     */
    static _fields = {};
    static isRecord(record) {
        return Boolean(record?.[IS_RECORD_SYM]);
    }
    /** @param {FIELD_SYM|RecordList} val */
    static isRelation(val) {
        if ([MANY_SYM, ONE_SYM].includes(val)) {
            return true;
        }
        return RecordList.isOne(val) || RecordList.isMany(val);
    }
    /** @param {FIELD_SYM} SYM */
    static isField(SYM) {
        return [MANY_SYM, ONE_SYM, ATTR_SYM].includes(SYM);
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
            if (expr in this._fields) {
                if (RecordList.isMany(this._fields[expr])) {
                    throw new Error("Using a Record.Many() as id is not (yet) supported");
                }
                if (!Record.isRelation(this._fields[expr])) {
                    return data[expr];
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
        obj.Model = this;
        const ids = this._retrieveIdFromData(data);
        let record = Object.assign(obj, {
            [IS_RECORD_SYM]: true,
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
    /**
     * @template T
     * @param {T} def;
     * @param {boolean} [html] if set, the field value contains html value.
     *   Useful to automatically markup when the insert is trusted.
     * @returns {T}
     */
    static attr(def, { html } = {}) {
        return [ATTR_SYM, { default: def, html }];
    }
    /** @returns {Record|Record[]} */
    static insert(data, options = {}) {
        const isMulti = Array.isArray(data);
        if (!isMulti) {
            data = [data];
        }
        const oldTrusted = Record.trusted;
        Record.trusted = options.html ?? Record.trusted;
        const res = data.map((d) => this._insert(d, options));
        Record.trusted = oldTrusted;
        if (!isMulti) {
            return res[0];
        }
        return res;
    }
    /** @returns {Record} */
    static _insert(data) {
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
    _fields = {};
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
            if (this.Model.id in this.Model._fields) {
                this[this.Model.id] = data;
            }
        }
    }

    delete() {
        const r1 = this;
        for (const name in r1._fields) {
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
                const l2 = r2._fields[name2];
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
        for (const [name, val] of Object.entries(this._fields)) {
            if (RecordList.isMany(val)) {
                data[name] = val.map((r) => r.toIdData());
            } else if (RecordList.isOne(val)) {
                data[name] = this[name]?.toIdData();
            } else {
                data[name] = this[name]; // Record.attr()
            }
        }
        delete data._store;
        delete data._fields;
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
