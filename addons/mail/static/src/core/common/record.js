/* @odoo-module */

import { onChange } from "@mail/utils/common/misc";
import { markRaw, markup, reactive, toRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const modelRegistry = registry.category("discuss.model");

/**
 * Class of markup, useful to detect content that is markup and to
 * automatically markup field during trusted insert
 */
const Markup = markup("").constructor;

/** @typedef {ATTR_SYM|MANY_SYM|ONE_SYM} FIELD_SYM */
const ATTR_SYM = Symbol("attr");
const MANY_SYM = Symbol("many");
const ONE_SYM = Symbol("one");
const OR_SYM = Symbol("or");
const AND_SYM = Symbol("and");
const IS_RECORD_SYM = Symbol("isRecord");
const IS_FIELD_SYM = Symbol("isField");

export function AND(...args) {
    return [AND_SYM, ...args];
}
export function OR(...args) {
    return [OR_SYM, ...args];
}

export function makeStore(env) {
    let storeReady = false;
    const res = {
        // fake store for now, until it becomes a model
        /** @type {import("models").Store} */
        store: {
            env,
            get: (...args) => BaseStore.prototype.get.call(this, ...args),
        },
    };
    const Models = {};
    for (const [name, _OgClass] of modelRegistry.getEntries()) {
        /** @type {typeof Record} */
        const OgClass = _OgClass;
        if (res.store[name]) {
            throw new Error(`There must be no duplicated Model Names (duplicate found: ${name})`);
        }
        // classes cannot be made reactive because they are functions and they are not supported.
        // work-around: make an object whose prototype is the class, so that static props become
        // instance props.
        /** @type {typeof Record} */
        const Model = Object.assign(Object.create(OgClass), { env, store: res.store });
        // Produce another class with changed prototype, so that there are automatic get/set on relational fields
        const Class = {
            [OgClass.name]: class extends OgClass {
                [IS_RECORD_SYM] = true;
                constructor() {
                    super();
                    const proxy = new Proxy(this, {
                        /** @param {Record} receiver */
                        get(target, name, receiver) {
                            if (name !== "_fields" && name in target._fields) {
                                const field = receiver._fields[name];
                                const rfield = target._fields[name];
                                if (
                                    (rfield.compute || rfield.sort) &&
                                    !rfield.eager &&
                                    !rfield.sorting &&
                                    !rfield.computing
                                ) {
                                    rfield.reading = true;
                                    Record.FR_QUEUE.push(rfield);
                                    if (rfield.compute) {
                                        rfield.computeInNeed = true;
                                    }
                                    if (rfield.sort) {
                                        rfield.sortInNeed = true;
                                    }
                                    if (rfield.computeOnNeed || rfield.sortOnNeed) {
                                        if (rfield.computeOnNeed) {
                                            rfield.computeOnNeed = false;
                                            rfield.computeInNeed = true;
                                            rfield.compute();
                                        }
                                        if (rfield.sortOnNeed) {
                                            rfield.sortOnNeed = false;
                                            rfield.sortInNeed = true;
                                            rfield.sort();
                                        }
                                    }
                                }
                                if (Record.isRelation(field)) {
                                    const l1 = field.value;
                                    if (RecordList.isMany(l1)) {
                                        return l1;
                                    }
                                    return l1[0];
                                }
                            }
                            return Reflect.get(target, name, receiver);
                        },
                        deleteProperty(target, name) {
                            return Record.MAKE_UPDATE(() => {
                                if (
                                    name !== "_fields" &&
                                    name in target._fields &&
                                    Record.isRelation(target._fields[name])
                                ) {
                                    const r1 = target;
                                    const l1 = r1._fields[name].value;
                                    l1.clear();
                                    return true;
                                }
                                const ret = Reflect.deleteProperty(target, name);
                                return ret;
                            });
                        },
                        /** @param {Record} receiver */
                        set(target, name, val, receiver) {
                            return Record.MAKE_UPDATE(() => {
                                if (name === "Model") {
                                    Reflect.set(target, name, val, receiver);
                                    return true;
                                }
                                if (target instanceof BaseStore && storeReady && name in Models) {
                                    // "store.Model =" is considered a Model.insert()
                                    res.store[name].insert(val);
                                    return true;
                                }
                                if (!(name in target.Model._fields)) {
                                    Reflect.set(target, name, val, receiver);
                                    return true;
                                }
                                if (Record.isAttr(target.Model._fields[name])) {
                                    if (
                                        target.Model._fields[name].html &&
                                        Record.trusted &&
                                        typeof val === "string" &&
                                        !(val instanceof Markup)
                                    ) {
                                        Reflect.set(target, name, markup(val), receiver);
                                    } else {
                                        Reflect.set(target, name, val, receiver);
                                    }
                                    return true;
                                }
                                /** @type {RecordList<Record>} */
                                const l1 = receiver._fields[name].value;
                                if (RecordList.isMany(l1)) {
                                    // [Record.many] =
                                    if (Record.isCommand(val)) {
                                        for (const [cmd, cmdData] of val) {
                                            if (Array.isArray(cmdData)) {
                                                for (const item of cmdData) {
                                                    if (cmd === "ADD") {
                                                        l1.add(item);
                                                    } else if (cmd === "ADD.noinv") {
                                                        l1._addNoinv(item);
                                                    } else if (cmd === "DELETE.noinv") {
                                                        l1._deleteNoinv(item);
                                                    } else {
                                                        l1.delete(item);
                                                    }
                                                }
                                            } else {
                                                if (cmd === "ADD") {
                                                    l1.add(cmdData);
                                                } else if (cmd === "ADD.noinv") {
                                                    l1._addNoinv(cmdData);
                                                } else if (cmd === "DELETE.noinv") {
                                                    l1._deleteNoinv(cmdData);
                                                } else {
                                                    l1.delete(cmdData);
                                                }
                                            }
                                        }
                                        return true;
                                    }
                                    if ([null, false, undefined].includes(val)) {
                                        l1.clear();
                                        return true;
                                    }
                                    if (!Array.isArray(val)) {
                                        val = [val];
                                    }
                                    l1.assign(val);
                                } else {
                                    // [Record.one] =
                                    if (Record.isCommand(val)) {
                                        const [cmd, cmdData] = val.at(-1);
                                        if (cmd === "ADD") {
                                            l1.add(cmdData);
                                        } else if (cmd === "ADD.noinv") {
                                            l1._addNoinv(cmdData);
                                        } else if (cmd === "DELETE.noinv") {
                                            l1._deleteNoinv(cmdData);
                                        } else {
                                            l1.delete(cmdData);
                                        }
                                        return true;
                                    }
                                    if ([null, false, undefined].includes(val)) {
                                        delete receiver[name];
                                        return true;
                                    }
                                    l1.add(val);
                                }
                                return true;
                            });
                        },
                    });
                    if (this instanceof BaseStore) {
                        res.store = proxy;
                    }
                    for (const name in Model._fields) {
                        const { compute, default: defaultVal, eager, sort } = Model._fields[name];
                        const SYM = this[name]?.[0];
                        this._fields[name] = { [SYM]: true, eager, name };
                        const field = this._fields[name];
                        if (Record.isRelation(SYM)) {
                            // Relational fields contain symbols for detection in original class.
                            // This constructor is called on genuine records:
                            // - 'one' fields => undefined
                            // - 'many' fields => RecordList
                            // this[name]?.[0] is ONE_SYM or MANY_SYM
                            const newVal = new RecordList(SYM);
                            if (this instanceof BaseStore) {
                                newVal.store = proxy;
                            } else {
                                newVal.store = res.store;
                            }
                            newVal.name = name;
                            newVal.owner = proxy;
                            field.value = newVal;
                            this.__uses__ = new RecordUses();
                            this[name] = newVal;
                        } else {
                            this[name] = defaultVal;
                        }
                        const rfield = toRaw(field);
                        onChange(proxy, name, () => (rfield.changed = true));
                        if (compute) {
                            const proxy2 = reactive(proxy, () => rfield.requestCompute());
                            Object.assign(rfield, {
                                compute: () => {
                                    // store is wrapped in another reactive, hence proxy is not enough
                                    const exactProxy = res.store.get(proxy.localId);
                                    if (!exactProxy) {
                                        return; // record was probably deleted;
                                    }
                                    rfield.computing = true;
                                    rfield.changed = false;
                                    exactProxy[name] = compute.call(proxy2);
                                    const changed = rfield.changed;
                                    rfield.changed = false;
                                    rfield.computing = false;
                                    return changed;
                                },
                                _compute: () => {
                                    // dummy call to keep reactive cb
                                    compute.call(proxy2);
                                },
                                requestCompute: ({ force = false } = {}) => {
                                    if (rfield.computing || rfield.sorting) {
                                        Record.ADD_QUEUE(field, "_compute");
                                        return;
                                    }
                                    if (Record.UPDATE !== 0 && !force) {
                                        Record.ADD_QUEUE(field, "compute");
                                    } else {
                                        if (rfield.eager) {
                                            rfield.compute();
                                        } else {
                                            rfield.computeOnNeed = true;
                                            if (rfield.computeInNeed) {
                                                rfield.computeInNeed = rfield.reading;
                                                rfield.computeOnNeed = false;
                                                const changed = rfield.compute();
                                                if (!changed) {
                                                    rfield.computeInNeed = true;
                                                }
                                            }
                                        }
                                    }
                                },
                            });
                        }
                        /** @type {Function} */
                        let observe;
                        if (sort) {
                            const proxy2 = reactive(proxy, () => rfield.requestSort());
                            Object.assign(rfield, {
                                sort: () => {
                                    // store is wrapped in another reactive, hence proxy is not enough
                                    const exactProxy = res.store.get(proxy.localId);
                                    if (!exactProxy) {
                                        return; // record was probably deleted;
                                    }
                                    rfield.sorting = true;
                                    rfield.changed = false;
                                    proxy2[name].sort(Model._fields[name].sort.bind(exactProxy));
                                    const changed = rfield.changed;
                                    rfield.changed = false;
                                    rfield.sorting = false;
                                    return changed;
                                },
                                _sort: () => {
                                    // dummy call to keep reactive cb
                                    proxy2[name]._sort(Model._fields[name].sort.bind(proxy2));
                                },
                                requestSort: ({ force } = {}) => {
                                    if (rfield.computing || rfield.sorting) {
                                        Record.ADD_QUEUE(field, "_sort");
                                        return;
                                    }
                                    if (Record.UPDATE !== 0 && !force) {
                                        Record.ADD_QUEUE(field, "sort");
                                    } else {
                                        if (rfield.eager) {
                                            rfield.sort();
                                        } else {
                                            rfield.sortOnNeed = true;
                                            if (rfield.sortInNeed) {
                                                rfield.sortInNeed = rfield.reading;
                                                rfield.sortOnNeed = false;
                                                const changed = rfield.sort();
                                                if (!changed) {
                                                    rfield.sortInNeed = true;
                                                }
                                            }
                                        }
                                    }
                                },
                            });
                        }
                        if (Model._fields[name].onUpdate) {
                            const fn = (record) => toRaw(Model)._fields[name].onUpdate.call(record);
                            Object.assign(rfield, {
                                onChange: () => {
                                    // store is wrapped in another reactive, hence proxy is not enough
                                    const exactProxy = res.store.get(proxy.localId);
                                    if (!exactProxy) {
                                        return; // record was probably deleted;
                                    }
                                    fn(exactProxy);
                                    observe?.();
                                },
                            });
                            Record._onChange(proxy, name, (obs) => {
                                observe = obs;
                                if (rfield.sorting) {
                                    observe();
                                    return;
                                }
                                if (Record.UPDATE !== 0) {
                                    Record.ADD_QUEUE(field, "onChange");
                                } else {
                                    field.onChange();
                                }
                            });
                        }
                    }
                    return proxy;
                }
            },
        }[OgClass.name];
        Object.assign(Model, {
            Class,
            records: JSON.parse(JSON.stringify(OgClass.records)),
            _fields: {},
        });
        Models[name] = Model;
        res.store[name] = Model;
        // Detect fields with a dummy record and setup getter/setters on them
        const obj = new OgClass();
        for (const [name, val] of Object.entries(obj)) {
            const SYM = val?.[0];
            if (!Record.isField(SYM)) {
                continue;
            }
            toRaw(Model)._fields[name] = { [IS_FIELD_SYM]: true, [SYM]: true, ...val[1] };
        }
    }
    // Sync inverse fields
    for (const Model of Object.values(Models)) {
        for (const [name, definition] of Object.entries(toRaw(Model)._fields)) {
            if (!Record.isRelation(definition)) {
                continue;
            }
            const { targetModel, inverse } = definition;
            if (targetModel && !Models[targetModel]) {
                throw new Error(`No target model ${targetModel} exists`);
            }
            if (inverse) {
                const rel2 = Models[targetModel]._fields[inverse];
                if (rel2.targetModel && rel2.targetModel !== Model.name) {
                    throw new Error(
                        `Fields ${Models[targetModel].name}.${inverse} has wrong targetModel. Expected: "${Model.name}" Actual: "${rel2.targetModel}"`
                    );
                }
                if (rel2.inverse && rel2.inverse !== name) {
                    throw new Error(
                        `Fields ${Models[targetModel].name}.${inverse} has wrong inverse. Expected: "${name}" Actual: "${rel2.inverse}"`
                    );
                }
                Object.assign(rel2, { targetModel: Model.name, inverse: name });
                // // FIXME: lazy fields are not working properly with inverse.
                definition.eager = true;
                rel2.eager = true;
            }
        }
    }
    // Make true store (as a model)
    res.store = reactive(res.store.Store.insert());
    res.store.env = env;
    for (const Model of Object.values(Models)) {
        Model.store = res.store;
        res.store[Model.name] = Model;
    }
    storeReady = true;
    return res.store;
}

class RecordUses {
    /**
     * Track the uses of a record. Each record contains a single `RecordUses`:
     * - Key: localId of record that uses current record
     * - Value: Map where key is relational field name, and value is number
     *          of time current record is present in this relation.
     *
     * @type {Map<string, Map<string, number>>}}
     */
    data = markRaw(new Map());
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

/** * @template {Record} R */
class RecordList extends Array {
    static isOne(list) {
        return Boolean(list?.[ONE_SYM]);
    }
    static isMany(list) {
        return Boolean(list?.[MANY_SYM]);
    }
    /** @type {Record} */
    owner;
    /** @type {string} */
    name;
    /** @type {import("models").Store} */
    store;
    /** @type {string[]} */
    data = [];

    get fieldDefinition() {
        return toRaw(toRaw(this).owner).Model._fields[toRaw(this).name];
    }

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
                return Record.MAKE_UPDATE(() => {
                    if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                        // support for "array[index] = r3" syntax
                        const index = parseInt(name);
                        receiver._insert(val, (r3) => {
                            const r2 = receiver[index];
                            if (r2 && r2.notEq(r3)) {
                                r2.__uses__.delete(receiver);
                            }
                            Record.ADD_QUEUE(receiver.owner._fields[receiver.name], "onDelete", r2);
                            const { inverse } = target.fieldDefinition;
                            if (inverse) {
                                r2._fields[inverse].value.delete(receiver);
                            }
                            receiver.data[index] = r3?.localId;
                            if (r3) {
                                r3.__uses__.add(receiver);
                                Record.ADD_QUEUE(
                                    receiver.owner._fields[receiver.name],
                                    "onAdd",
                                    r3
                                );
                                const { inverse } = target.fieldDefinition;
                                if (inverse) {
                                    r3._fields[inverse].value.add(receiver);
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
                });
            },
        });
    }
    /**
     * @param {R|any} val
     * @param {(R) => void} [fn] function that is called in-between preinsert and
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
        const { inverse } = this.fieldDefinition;
        if (inverse && inv) {
            // special command to call _addNoinv/_deleteNoInv, to prevent infinite loop
            val[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", this.owner]];
        }
        /** @type {R} */
        let r3;
        if (!Record.isRecord(val)) {
            const { targetModel } = this.fieldDefinition;
            r3 = this.store[targetModel].preinsert(val);
        } else {
            r3 = val;
        }
        fn?.(r3);
        if (!Record.isRecord(val)) {
            // was preinserted, fully insert now
            const { targetModel } = this.fieldDefinition;
            this.store[targetModel].insert(val);
        }
        return r3;
    }
    /** @param {R[]|any[]} data */
    assign(data) {
        return Record.MAKE_UPDATE(() => {
            /** @type {Record[]|Set<Record>|RecordList<Record|any[]>} */
            const collection = Record.isRecord(data) ? [data] : data;
            // l1 and collection could be same record list,
            // save before clear to not push mutated recordlist that is empty
            const vals = [...collection];
            /** @type {R[]} */
            const oldRecords = this.slice();
            for (const r2 of oldRecords) {
                r2.__uses__.delete(this);
            }
            const records = vals.map((val) =>
                this._insert(val, (r3) => {
                    r3.__uses__.add(this);
                })
            );
            this.data = records.map((r) => r.localId);
        });
    }
    /** @param {R[]} records */
    push(...records) {
        return Record.MAKE_UPDATE(() => {
            for (const val of records) {
                const r = this._insert(val, (r3) => {
                    this.data.push(r3.localId);
                    r3.__uses__.add(this);
                });
                Record.ADD_QUEUE(this.owner._fields[this.name], "onAdd", r);
                const { inverse } = this.fieldDefinition;
                if (inverse) {
                    r._fields[inverse].value.add(this.owner);
                }
            }
            return this.data.length;
        });
    }
    /** @returns {R} */
    pop() {
        return Record.MAKE_UPDATE(() => {
            /** @type {R} */
            const r2 = this.at(-1);
            if (r2) {
                this.splice(this.length - 1, 1);
            }
            return r2;
        });
    }
    /** @returns {R} */
    shift() {
        return Record.MAKE_UPDATE(() => {
            const r2 = this.store.get(this.data.shift());
            r2?.__uses__.delete(this);
            if (r2) {
                Record.ADD_QUEUE(this.owner._fields[this.name], "onDelete", r2);
                const { inverse } = this.fieldDefinition;
                if (inverse) {
                    r2._fields[inverse].value.delete(this.owner);
                }
            }
            return r2;
        });
    }
    /** @param {R[]} records */
    unshift(...records) {
        return Record.MAKE_UPDATE(() => {
            for (let i = records.length - 1; i >= 0; i--) {
                const r = this._insert(records[i], (r3) => {
                    this.data.unshift(r3.localId);
                    r3.__uses__.add(this);
                });
                Record.ADD_QUEUE(this.owner._fields[this.name], "onAdd", r);
                const { inverse } = this.fieldDefinition;
                if (inverse) {
                    r._fields[inverse].value.add(this.owner);
                }
            }
            return this.data.length;
        });
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
        return Record.MAKE_UPDATE(() => {
            const oldRecords = this.slice(start, start + deleteCount);
            const list = this.data.slice(); // splice on copy of list so that reactive observers not triggered while splicing
            list.splice(start, deleteCount, ...newRecords.map((r) => r.localId));
            this.data = list;
            for (const r of oldRecords) {
                r.__uses__.delete(this);
                Record.ADD_QUEUE(this.owner._fields[this.name], "onDelete", r);
                const { inverse } = this.fieldDefinition;
                if (inverse) {
                    r._fields[inverse].value.delete(this.owner);
                }
            }
            for (const r of newRecords) {
                r.__uses__.add(this);
                Record.ADD_QUEUE(this.owner._fields[this.name], "onAdd", r);
                const { inverse } = this.fieldDefinition;
                if (inverse) {
                    r._fields[inverse].value.add(this.owner);
                }
            }
        });
    }
    /** @param {(a: R, b: R) => boolean} func */
    sort(func) {
        return Record.MAKE_UPDATE(() => {
            const list = this.data.slice(); // sort on copy of list so that reactive observers not triggered while sorting
            list.sort((a, b) => func(this.store.get(a), this.store.get(b)));
            this.data = list;
        });
    }
    /**
     * Dummy sort just to re-tag everything for reactive callback. This has no effect on data in record list.
     *
     * @param {(a: R, b: R) => boolean} func
     */
    _sort(func) {
        return Record.MAKE_UPDATE(() => {
            const list = this.data.slice(); // sort on copy of list so that reactive observers not triggered while sorting
            list.sort((a, b) => func(this.store.get(a), this.store.get(b)));
        });
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        return this.data
            .map((localId) => this.store.get(localId))
            .concat(...collections.map((c) => [...c]));
    }
    /** @param {...R}  */
    add(...records) {
        return Record.MAKE_UPDATE(() => {
            if (RecordList.isOne(this)) {
                const last = records.at(-1);
                if (Record.isRecord(last) && last.in(toRaw(this))) {
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
                if (Record.isRecord(val) && val.in(toRaw(this))) {
                    continue;
                }
                this._insert(val, (r) => {
                    if (this.indexOf(r) === -1) {
                        this.push(r);
                    }
                });
            }
        });
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
            if (Record.isRecord(last) && last.in(toRaw(this))) {
                return;
            }
            const record = this._insert(
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
            Record.ADD_QUEUE(this.owner._fields[this.name], "onAdd", record);
            return;
        }
        for (const val of records) {
            if (Record.isRecord(val) && val.in(toRaw(this))) {
                continue;
            }
            const record = this._insert(
                val,
                (r) => {
                    if (this.indexOf(r) === -1) {
                        this.data.push(r.localId);
                        r.__uses__.add(this);
                    }
                },
                { inv: false }
            );
            Record.ADD_QUEUE(this.owner._fields[this.name], "onAdd", record);
        }
    }
    /** @param {...R}  */
    delete(...records) {
        return Record.MAKE_UPDATE(() => {
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
        });
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
            const record = this._insert(
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
            Record.ADD_QUEUE(this.owner._fields[this.name], "onDelete", record);
        }
    }
    clear() {
        return Record.MAKE_UPDATE(() => {
            while (this.data.length > 0) {
                this.pop();
            }
        });
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
 * @property {() => any} [compute] if set the field is computed based on provided function.
 *   The `this` of function is the record, and the function is recalled whenever any field
 *   in models used by this compute function is changed. The return value is the new value of
 *   the field. On relational field, passing a (list of) record(s) or data work as expected.
 * @property {boolean} [eager=false] when field is computed, determines whether the computation
 *   of this field is eager or lazy. By default, fields are computed lazily, which means that
 *   they are computed when dependencies change AND when this field is being used. In eager mode,
 *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
 *   behaviour of OWL reactive.
 * @property {string} [inverse] name of inverse relational field in targetModel.
 * @property {(r: Record) => void} [onAdd] hook that is called when relation is updated
 *   with a record being added. Callback param is record being added into relation.
 * @property {(r: Record) => void} [onDelete] hook that is called when relation is updated
 *   with a record being deleted. Callback param is record being deleted from relation.
 * @property {() => void} [onUpdate] hook that is called when field is updated.
 * @property {(r1: Record, r2: Record) => number} [sort] if defined, this many relational field is
 *   automatically sorted by this function.
 */
/**
 * @typedef {Object} RecordField
 * @property {string} name the name of the field in the model definition
 * @property {boolean} [ATTR_SYM] true when this is an attribute, i.e. a non-relational field.
 * @property {boolean} [MANY_SYM] true when this is a many relation.
 * @property {boolean} [ONE_SYM] true when this is a one relation.
 * @property {any} [default] the default value of this attribute.
 * @property {() => void} [compute] for computed field, invoking this function (re-)computes the field.
 * @property {boolean} [computing] for computed field, determines whether the field is computing its value.
 * @property {() => void} [requestCompute] on computed field, calling this function makes a request to compute
 *   the field. This doesn't necessarily mean the field is immediately re-computed: during an update cycle, this
 *   is put in the compute FC_QUEUE and will be invoked at end.
 * @property {boolean} [computeOnNeed] on lazy-computed field, determines whether the field should be (re-)computed
 *   when it's needed (i.e. accessed). Eager computed fields are immediately re-computed at end of update cycle,
 *   whereas lazy computed fields wait extra for them being needed.
 * @property {boolean} [computeInNeed] on lazy computed-fields, determines whether this field is needed (i.e. accessed).
 *   This is only set when there's a get on this lazy computed-field during an update cycle (UPDATE !== 0), as computed
 *   fields are invoked only at the end of an update cycle. When outside of an update cycle, only `computeOnNeed`
 *   determines (re-)computation.
 * @property {() => void} [_compute] on computed field, function to trigger observing of sort without side-effect to actually
 *   compute the field. Since OWL reactive are consumable and their callback can be triggered during a sorting in update cycle,
 *   there's likely a need to re-observe the reactive. This function is handy for this specific case for the compute.
 * @property {() => void} [sort] for sorted field, invoking this function (re-)sorts the field.
 * @property {boolean} [sorting] for sorted field, determines whether the field is sorting its value.
 * @property {() => void} [requestSort] on sorted field, calling this function makes a request to sort
 *   the field. This doesn't necessarily mean the field is immediately re-sorted: during an update cycle, this
 *   is put in the sort FS_QUEUE and will be invoked at end.
 * @property {boolean} [sortOnNeed] on lazy-sorted field, determines whether the field should be (re-)sorted
 *   when it's needed (i.e. accessed). Eager sorted fields are immediately re-sorted at end of update cycle,
 *   whereas lazy sorted fields wait extra for them being needed.
 * @property {boolean} [sortInNeed] on lazy sorted-fields, determines whether this field is needed (i.e. accessed).
 *   This is only set when there's a get on this lazy sorted-field during an update cycle (UPDATE !== 0), as sorted
 *   fields are invoked only at the end of an update cycle. When outside of an update cycle, only `sortOnNeed`
 *   determines (re-)sort.
 * @property {boolean} [reading] on computed and sorted field, determines whether the field is being read during the
 *   current update cycle. Useful to preserve compute/sortInNeed whenever the fields need compute/sort. This is cleared
 *   automatically after the update cycle.
 * @property {boolean} [changed] on computed and sorted field, determines whether the field has been changed by the compute
 *   or sort. This is useful to keep track of "in-need" flags when the compute and/or sort did not change the field value.
 * @property {() => void} [_sort] on sorted field, function to trigger observing of sort without side-effect to actually
 *   sort the field. Since OWL reactive are consumable and their callback can be triggered during a sorting in update cycle,
 *   there's likely a need to re-observe the reactive. This function is handy for this specific case for the sort.
 * @property {() => void} [onChange] function that contains functions to be called when the value of field
 *   has changed, e.g. sort and onUpdate.
 * @property {RecordList<Record>} [value] value of the field. Either its raw value if it's an attribute,
 *   or a RecordList if it's a relational field.
 */

export class Record {
    /** @param {FieldDefinition} */
    static isAttr(definition) {
        return Boolean(definition?.[ATTR_SYM]);
    }
    /**
     * Determines whether the inserts are considered trusted or not.
     * Useful to auto-markup html fields when this is set
     */
    static trusted = false;
    static id;
    /** @type {Object<string, Record>} */
    static records = {};
    /** @type {import("models").Store} */
    static store;
    /** @type {RecordField[]} */
    static FC_QUEUE = []; // field-computes
    /** @type {RecordField[]} */
    static FC2_QUEUE = []; // field-computes (dummy _compute, i.e. observing of compute, see Record._compute)
    /** @type {RecordField[]} */
    static FR_QUEUE = []; // field-readings
    /** @type {RecordField[]} */
    static FS_QUEUE = []; // field-sorts
    /** @type {RecordField[]} */
    static FS2_QUEUE = []; // field-sorts (dummy _sort, i.e. observing of sort, see RecordField._sort)
    /** @type {Aray<{field: RecordField, records: Record[]}>} */
    static FA_QUEUE = []; // field-onadds
    /** @type {Aray<{field: RecordField, records: Record[]}>} */
    static FD_QUEUE = []; // field-ondeletes
    /** @type {RecordField[]} */
    static FO_QUEUE = []; // field-onchanges
    /** @type {Function[]} */
    static RO_QUEUE = []; // record-onchanges
    /** @type {Record[]} */
    static RD_QUEUE = []; // record-deletes
    static UPDATE = 0;
    /** @param {() => any} fn */
    static MAKE_UPDATE(fn) {
        const selfRaw = toRaw(this);
        selfRaw.UPDATE++;
        const res = fn();
        selfRaw.UPDATE--;
        if (selfRaw.UPDATE === 0) {
            // pretend an increased update cycle so that nothing in queue creates many small update cycles
            selfRaw.UPDATE++;
            while (
                selfRaw.FC_QUEUE.length > 0 ||
                selfRaw.FC2_QUEUE.length > 0 ||
                selfRaw.FS_QUEUE.length > 0 ||
                selfRaw.FS2_QUEUE.length > 0 ||
                selfRaw.FA_QUEUE.length > 0 ||
                selfRaw.FD_QUEUE.length > 0 ||
                selfRaw.FO_QUEUE.length > 0 ||
                selfRaw.RO_QUEUE.length > 0 ||
                selfRaw.RD_QUEUE.length > 0
            ) {
                const FC_QUEUE = [...selfRaw.FC_QUEUE];
                const FC2_QUEUE = [...selfRaw.FC2_QUEUE];
                const FS_QUEUE = [...selfRaw.FS_QUEUE];
                const FS2_QUEUE = [...selfRaw.FS2_QUEUE];
                const FA_QUEUE = [...selfRaw.FA_QUEUE];
                const FD_QUEUE = [...selfRaw.FD_QUEUE];
                const FO_QUEUE = [...selfRaw.FO_QUEUE];
                const RO_QUEUE = [...selfRaw.RO_QUEUE];
                const RD_QUEUE = [...selfRaw.RD_QUEUE];
                selfRaw.FC_QUEUE = [];
                selfRaw.FC2_QUEUE = [];
                selfRaw.FS_QUEUE = [];
                selfRaw.FS2_QUEUE = [];
                selfRaw.FA_QUEUE = [];
                selfRaw.FD_QUEUE = [];
                selfRaw.FO_QUEUE = [];
                selfRaw.RO_QUEUE = [];
                selfRaw.RD_QUEUE = [];
                while (FC_QUEUE.length > 0) {
                    const field = FC_QUEUE.pop();
                    field.requestCompute({ force: true });
                }
                while (FS_QUEUE.length > 0) {
                    const field = FS_QUEUE.pop();
                    field.requestSort({ force: true });
                }
                while (FC2_QUEUE.length > 0) {
                    const field = FC2_QUEUE.pop();
                    field._compute();
                }
                while (FS2_QUEUE.length > 0) {
                    const field = FS2_QUEUE.pop();
                    field._sort();
                }
                while (FA_QUEUE.length > 0) {
                    const { field, records } = FA_QUEUE.pop();
                    const { onAdd } = field.value.fieldDefinition;
                    records.forEach((record) => onAdd?.call(field.value.owner, record));
                }
                while (FD_QUEUE.length > 0) {
                    const { field, records } = FD_QUEUE.pop();
                    const { onDelete } = field.value.fieldDefinition;
                    records.forEach((record) => onDelete?.call(field.value.owner, record));
                }
                while (FO_QUEUE.length > 0) {
                    const field = FO_QUEUE.pop();
                    field.onChange();
                }
                while (RO_QUEUE.length > 0) {
                    const cb = RO_QUEUE.pop();
                    cb();
                }
                while (RD_QUEUE.length > 0) {
                    const record = RD_QUEUE.pop();
                    // effectively delete the record
                    for (const name in record._fields) {
                        record[name] = undefined;
                    }
                    for (const [localId, names] of record.__uses__.data.entries()) {
                        for (const [name2, count] of names.entries()) {
                            const r2 = record._store.get(localId);
                            if (!r2) {
                                // record already deleted, clean inverses
                                record.__uses__.data.delete(localId);
                                continue;
                            }
                            const l2 = r2._fields[name2].value;
                            if (RecordList.isMany(l2)) {
                                for (let c = 0; c < count; c++) {
                                    r2[name2].delete(record);
                                }
                            } else {
                                r2[name2] = undefined;
                            }
                        }
                    }
                    delete record.Model.records[record.localId];
                }
            }
            while (selfRaw.FR_QUEUE.length > 0) {
                const field = selfRaw.FR_QUEUE.pop();
                field.reading = false;
            }
            selfRaw.UPDATE--;
        }
        return res;
    }
    /**
     * @param {RecordField|Record} fieldOrRecord
     * @param {"compute"|"sort"|"onAdd"|"onDelete"|"onChange"|"_compute"|"_sort"} type
     * @param {Record} [record] when field with onAdd/onDelete, the record being added or deleted
     */
    static ADD_QUEUE(fieldOrRecord, type, record) {
        const selfRaw = toRaw(this);
        if (Record.isRecord(fieldOrRecord)) {
            /** @type {Record} */
            const record = fieldOrRecord;
            const rawRecord = toRaw(record);
            if (type === "delete") {
                if (!selfRaw.RD_QUEUE.some((r) => toRaw(r) === rawRecord)) {
                    selfRaw.RD_QUEUE.push(rawRecord);
                }
            }
        } else {
            /** @type {RecordField} */
            const field = fieldOrRecord;
            const rawField = toRaw(field);
            if (type === "compute") {
                if (!selfRaw.FC_QUEUE.some((f) => toRaw(f) === rawField)) {
                    selfRaw.FC_QUEUE.push(field);
                }
            }
            if (type === "sort") {
                if (!rawField.value?.fieldDefinition.sort) {
                    return;
                }
                if (!selfRaw.FS_QUEUE.some((f) => toRaw(f) === rawField)) {
                    selfRaw.FS_QUEUE.push(field);
                }
            }
            if (type === "onAdd") {
                if (rawField.value?.fieldDefinition.sort) {
                    this.ADD_QUEUE(fieldOrRecord, "sort");
                }
                if (!rawField.value?.fieldDefinition.onAdd) {
                    return;
                }
                const item = selfRaw.FA_QUEUE.find((item) => toRaw(item.field) === rawField);
                if (!item) {
                    selfRaw.FA_QUEUE.push({ field, records: [record] });
                } else {
                    if (!item.records.some((r) => r.eq(record))) {
                        item.records.push(record);
                    }
                }
            }
            if (type === "onDelete") {
                if (!rawField.value?.fieldDefinition.onDelete) {
                    return;
                }
                const item = selfRaw.FD_QUEUE.find((item) => toRaw(item.field) === rawField);
                if (!item) {
                    selfRaw.FD_QUEUE.push({ field, records: [record] });
                } else {
                    if (!item.records.some((r) => r.eq(record))) {
                        item.records.push(record);
                    }
                }
            }
            if (type === "onChange") {
                if (!selfRaw.FO_QUEUE.some((f) => toRaw(f) === rawField)) {
                    selfRaw.FO_QUEUE.push(field);
                }
            }
            if (type === "_compute") {
                if (!selfRaw.FC2_QUEUE.some((f) => toRaw(f) === rawField)) {
                    selfRaw.FC2_QUEUE.push(field);
                }
            }
            if (type === "_sort") {
                if (!selfRaw.FS2_QUEUE.some((f) => toRaw(f) === rawField)) {
                    selfRaw.FS2_QUEUE.push(field);
                }
            }
        }
    }
    static onChange(record, name, cb) {
        const selfRaw = toRaw(this);
        this._onChange(record, name, (observe) => {
            const fn = () => {
                observe();
                cb();
            };
            if (selfRaw.UPDATE !== 0) {
                if (!selfRaw.RO_QUEUE.some((f) => toRaw(f) === fn)) {
                    selfRaw.RO_QUEUE.push(fn);
                }
            } else {
                fn();
            }
        });
    }
    /**
     * Version of onChange where the callback receives observe function as param.
     * This is useful when there's desire to postpone calling the callback function,
     * in which the observe is also intended to have its invocation postponed.
     *
     * @param {Record} record
     * @param {string|string[]} key
     * @param {(observe: Function) => any} callback
     */
    static _onChange(record, key, callback) {
        let proxy;
        function _observe() {
            // observe should not flag the field as in need
            let oldComputeInNeed;
            let oldSortInNeed;
            if (record[IS_RECORD_SYM] && toRaw(record)._fields[key]) {
                oldComputeInNeed = toRaw(record)._fields[key].computeInNeed;
                oldSortInNeed = toRaw(record)._fields[key].sortInNeed;
            }
            void proxy[key];
            if (proxy[key] instanceof Object) {
                void Object.keys(proxy[key]);
            }
            if (proxy[key] instanceof Array) {
                void proxy[key].length;
                void proxy[key].forEach((i) => i);
            }
            if (record[IS_RECORD_SYM] && record._fields[key]) {
                toRaw(record)._fields[key].computeInNeed = oldComputeInNeed;
                toRaw(record)._fields[key].sortInNeed = oldSortInNeed;
            }
        }
        if (Array.isArray(key)) {
            for (const k of key) {
                this._onChange(record, k, callback);
            }
            return;
        }
        proxy = reactive(record, () => callback(_observe));
        _observe();
        return proxy;
    }
    /**
     * Contains field definitions of the model:
     * - key : field name
     * - value: Value contains definition of field
     *
     * @type {Object.<string, FieldDefinition>}
     */
    static _fields = markRaw({});
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
        return Record.MAKE_UPDATE(() => {
            const obj = new this.Class();
            obj.Model = this;
            const ids = this._retrieveIdFromData(data);
            for (const name in ids) {
                if (
                    ids[name] &&
                    !Record.isRecord(ids[name]) &&
                    !Record.isCommand(ids[name]) &&
                    Record.isRelation(this._fields[name])
                ) {
                    // preinsert that record in relational field,
                    // as it is required to make current local id
                    ids[name] = this.store[this._fields[name].targetModel].preinsert(ids[name]);
                }
            }
            let record = Object.assign(obj, {
                localId: this.localId(ids),
                ...ids,
            });
            Object.assign(record, { _store: this.store });
            this.records[record.localId] = record;
            // return reactive version
            record = this.records[record.localId];
            for (const field of Object.values(record._fields)) {
                field.requestCompute?.();
                field.requestSort?.();
            }
            return record;
        });
    }
    /**
     * @template {keyof import("models").Models} M
     * @param {M} targetModel
     * @param {Object} [param1={}]
     * @param {Function} [param1.compute] if set, the value of this relational field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * * @property {boolean} [eager=false] when field is computed, determines whether the computation
     *   of this field is eager or lazy. By default, fields are computed lazily, which means that
     *   they are computed when dependencies change AND when this field is being used. In eager mode,
     *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
     *   behaviour of OWL reactive.
     * @param {string} [param1.inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(r: import("models").Models[M]) => void} [param1.onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(r: import("models").Models[M]) => void} [param1.onDelete] function that is called when a record is removed
     *   from the relation.
     * @param {() => void} [param1.onUpdate] function that is called when the field value is updated.
     *   This is called at least once at record creation.
     * @returns {import("models").Models[M]}
     */
    static one(targetModel, { compute, eager = false, inverse, onAdd, onDelete, onUpdate } = {}) {
        return [ONE_SYM, { targetModel, compute, eager, inverse, onAdd, onDelete, onUpdate }];
    }
    /**
     * @template {keyof import("models").Models} M
     * @param {M} targetModel
     * @param {Object} [param1={}]
     * @param {Function} [param1.compute] if set, the value of this relational field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @property {boolean} [eager=false] when field is computed, determines whether the computation
     *   of this field is eager or lazy. By default, fields are computed lazily, which means that
     *   they are computed when dependencies change AND when this field is being used. In eager mode,
     *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
     *   behaviour of OWL reactive.
     * @param {string} [param1.inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(r: import("models").Models[M]) => void} [param1.onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(r: import("models").Models[M]) => void} [param1.onDelete] function that is called when a record is removed
     *   from the relation.
     * @param {() => void} [param1.onUpdate] function that is called when the field value is updated.
     *   This is called at least once at record creation.
     * @property {(r1: import("models").Models[M], r2: import("models").Models[M]) => number} [sort] if defined, this field
     *   is automatically sorted by this function.
     * @returns {import("models").Models[M][]}
     */
    static many(
        targetModel,
        { compute, eager = false, inverse, onAdd, onDelete, onUpdate, sort } = {}
    ) {
        return [
            MANY_SYM,
            { targetModel, compute, eager, inverse, onAdd, onDelete, onUpdate, sort },
        ];
    }
    /**
     * @template T
     * @param {T} def
     * @param {Object} [param1={}]
     * @param {Function} [param1.compute] if set, the value of this attr field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @property {boolean} [eager=false] when field is computed, determines whether the computation
     *   of this field is eager or lazy. By default, fields are computed lazily, which means that
     *   they are computed when dependencies change AND when this field is being used. In eager mode,
     *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
     *   behaviour of OWL reactive.
     * @param {boolean} [param1.html] if set, the field value contains html value.
     *   Useful to automatically markup when the insert is trusted.
     * @param {() => void} [param1.onUpdate] function that is called when the field value is updated.
     *   This is called at least once at record creation.
     * @returns {T}
     */
    static attr(def, { compute, eager = false, html, onUpdate } = {}) {
        return [ATTR_SYM, { compute: compute, default: def, eager, html, onUpdate }];
    }
    /** @returns {Record|Record[]} */
    static insert(data, options = {}) {
        return Record.MAKE_UPDATE(() => {
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
        });
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
     * Raw relational values of the record, each of which contains object id(s)
     * rather than the record(s). This allows data in store and models being normalized,
     * which eases handling relations notably in when a record gets deleted.
     *
     * @type {Object<string, RecordField>}
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
        return Record.MAKE_UPDATE(() => {
            if (typeof data === "object" && data !== null) {
                Object.assign(this, data);
            } else {
                // update on single-id data
                if (this.Model.id in toRaw(this).Model._fields) {
                    this[this.Model.id] = data;
                }
            }
        });
    }

    delete() {
        return Record.MAKE_UPDATE(() => Record.ADD_QUEUE(this, "delete"));
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
        for (const [name, { value }] of Object.entries(this._fields)) {
            if (RecordList.isMany(value)) {
                data[name] = value.map((r) => r.toIdData());
            } else if (RecordList.isOne(value)) {
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

export class BaseStore extends Record {
    /**
     * @param {string} localId
     * @returns {Record}
     */
    get(localId) {
        if (typeof localId !== "string") {
            return undefined;
        }
        const modelName = Record.modelFromLocalId(localId);
        if (modelName === "Store") {
            return this;
        }
        return this[modelName].records[localId];
    }
}
