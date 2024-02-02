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

/**
 * @param {Record} record
 * @param {Object} vals
 */
function updateFields(record, vals) {
    for (const [fieldName, value] of Object.entries(vals)) {
        if (record instanceof BaseStore && record.storeReady && fieldName in record.Models) {
            // "store[Model] =" is considered a Model.insert()
            record[fieldName].insert(value);
        } else {
            const fieldDefinition = record.Model._fields.get(fieldName);
            if (!fieldDefinition || Record.isAttr(fieldDefinition)) {
                updateAttr(record, fieldName, value);
            } else {
                updateRelation(record, fieldName, value);
            }
        }
    }
}

/**
 * @param {Record} record
 * @param {string} fieldName
 * @param {any} value
 */
function updateAttr(record, fieldName, value) {
    const fieldDefinition = record.Model._fields.get(fieldName);
    // ensure each field write goes through the proxy exactly once to trigger reactives
    const targetRecord = record._proxyUsed.has(fieldName) ? record : record._proxy;
    let shouldChange = record[fieldName] !== value;
    let newValue = value;
    if (fieldDefinition?.html && Record.trusted) {
        shouldChange =
            record[fieldName]?.toString() !== value?.toString() ||
            !(record[fieldName] instanceof Markup);
        newValue = typeof value === "string" ? markup(value) : value;
    }
    if (shouldChange) {
        record._updateFields.add(fieldName);
        targetRecord[fieldName] = newValue;
        record._updateFields.delete(fieldName);
    }
}

/**
 * @param {Record} record
 * @param {string} fieldName
 * @param {any} value
 */
function updateRelation(record, fieldName, value) {
    /** @type {RecordList<Record>} */
    const recordList = record._fields.get(fieldName).value;
    if (RecordList.isMany(recordList)) {
        updateRelationMany(recordList, value);
    } else {
        updateRelationOne(recordList, value);
    }
}

/**
 * @param {RecordList} recordList
 * @param {any} value
 */
function updateRelationMany(recordList, value) {
    if (Record.isCommand(value)) {
        for (const [cmd, cmdData] of value) {
            if (Array.isArray(cmdData)) {
                for (const item of cmdData) {
                    if (cmd === "ADD") {
                        recordList.add(item);
                    } else if (cmd === "ADD.noinv") {
                        recordList._addNoinv(item);
                    } else if (cmd === "DELETE.noinv") {
                        recordList._deleteNoinv(item);
                    } else {
                        recordList.delete(item);
                    }
                }
            } else {
                if (cmd === "ADD") {
                    recordList.add(cmdData);
                } else if (cmd === "ADD.noinv") {
                    recordList._addNoinv(cmdData);
                } else if (cmd === "DELETE.noinv") {
                    recordList._deleteNoinv(cmdData);
                } else {
                    recordList.delete(cmdData);
                }
            }
        }
    } else if ([null, false, undefined].includes(value)) {
        recordList.clear();
    } else if (!Array.isArray(value)) {
        recordList.assign([value]);
    } else {
        recordList.assign(value);
    }
}

/**
 * @param {RecordList} recordList
 * @param {any} value
 * @returns {boolean} whether the value has changed
 */
function updateRelationOne(recordList, value) {
    if (Record.isCommand(value)) {
        const [cmd, cmdData] = value.at(-1);
        if (cmd === "ADD") {
            recordList.add(cmdData);
        } else if (cmd === "ADD.noinv") {
            recordList._addNoinv(cmdData);
        } else if (cmd === "DELETE.noinv") {
            recordList._deleteNoinv(cmdData);
        } else {
            recordList.delete(cmdData);
        }
    } else if ([null, false, undefined].includes(value)) {
        recordList.clear();
    } else {
        recordList.add(value);
    }
}

function sortRecordList(recordListFullProxy, func) {
    const recordList = toRaw(recordListFullProxy)._raw;
    // sort on copy of list so that reactive observers not triggered while sorting
    const recordsFullProxy = recordListFullProxy.data.map((localId) =>
        recordListFullProxy.store.recordByLocalId.get(localId)
    );
    recordsFullProxy.sort(func);
    const data = recordsFullProxy.map((recordFullProxy) => toRaw(recordFullProxy)._raw.localId);
    const hasChanged = recordList.data.some((localId, i) => localId !== data[i]);
    if (hasChanged) {
        recordListFullProxy.data = data;
    }
}

export function makeStore(env) {
    Record.UPDATE = 0;
    const recordByLocalId = reactive(new Map());
    const res = {
        // fake store for now, until it becomes a model
        /** @type {import("models").Store} */
        store: {
            env,
            get: (...args) => BaseStore.prototype.get.call(this, ...args),
            recordByLocalId,
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
        const Model = Object.create(OgClass);
        // Produce another class with changed prototype, so that there are automatic get/set on relational fields
        const Class = {
            [OgClass.name]: class extends OgClass {
                [IS_RECORD_SYM] = true;
                constructor() {
                    super();
                    const record = this;
                    record._proxyUsed = new Set();
                    record._updateFields = new Set();
                    record._raw = record;
                    record.Model = Model;
                    const recordProxyInternal = new Proxy(record, {
                        get(record, name, recordFullProxy) {
                            recordFullProxy = record._downgradeProxy(recordFullProxy);
                            const field = record._fields.get(name);
                            if (field) {
                                if (field.compute && !field.eager) {
                                    field.computeInNeed = true;
                                    if (field.computeOnNeed) {
                                        field.compute();
                                    }
                                }
                                if (field.sort && !field.eager) {
                                    field.sortInNeed = true;
                                    if (field.sortOnNeed) {
                                        field.sort();
                                    }
                                }
                                if (Record.isRelation(field)) {
                                    const recordList = field.value;
                                    const recordListFullProxy =
                                        recordFullProxy._fields.get(name).value._proxy;
                                    if (RecordList.isMany(recordList)) {
                                        return recordListFullProxy;
                                    }
                                    return recordListFullProxy[0];
                                }
                            }
                            return Reflect.get(record, name, recordFullProxy);
                        },
                        deleteProperty(record, name) {
                            return Record.MAKE_UPDATE(function recordDeleteProperty() {
                                const field = record._fields.get(name);
                                if (field && Record.isRelation(field)) {
                                    const recordList = field.value;
                                    recordList.clear();
                                    return true;
                                }
                                return Reflect.deleteProperty(record, name);
                            });
                        },
                        /**
                         * Using record.update(data) is preferable for performance to batch process
                         * when updating multiple fields at the same time.
                         */
                        set(record, name, val) {
                            // ensure each field write goes through the updateFields method exactly once
                            if (record._updateFields.has(name)) {
                                record[name] = val;
                                return true;
                            }
                            return Record.MAKE_UPDATE(function recordSet() {
                                record._proxyUsed.add(name);
                                updateFields(record, { [name]: val });
                                record._proxyUsed.delete(name);
                                return true;
                            });
                        },
                    });
                    record._proxyInternal = recordProxyInternal;
                    const recordProxy = reactive(recordProxyInternal);
                    record._proxy = recordProxy;
                    if (record instanceof BaseStore) {
                        res.store = record;
                    }
                    for (const [name, fieldDefinition] of Model._fields) {
                        const SYM = record[name]?.[0];
                        const field = { [SYM]: true, eager: fieldDefinition.eager, name };
                        record._fields.set(name, field);
                        if (Record.isRelation(SYM)) {
                            // Relational fields contain symbols for detection in original class.
                            // This constructor is called on genuine records:
                            // - 'one' fields => undefined
                            // - 'many' fields => RecordList
                            // record[name]?.[0] is ONE_SYM or MANY_SYM
                            const recordList = new RecordList();
                            Object.assign(recordList, {
                                [SYM]: true,
                                field,
                                name,
                                owner: record,
                                _raw: recordList,
                            });
                            recordList.store = res.store;
                            field.value = recordList;
                        } else {
                            record[name] = fieldDefinition.default;
                        }
                        if (fieldDefinition.compute) {
                            if (!fieldDefinition.eager) {
                                onChange(recordProxy, name, () => {
                                    if (field.computing) {
                                        /**
                                         * Use a reactive to reset the computeInNeed flag when there is
                                         * a change. This assumes when other reactive are still
                                         * observing the value, its own callback will reset the flag to
                                         * true through the proxy getters.
                                         */
                                        field.computeInNeed = false;
                                    }
                                });
                                // reset flags triggered by registering onChange
                                field.computeInNeed = false;
                                field.sortInNeed = false;
                            }
                            const proxy2 = reactive(recordProxy, function computeObserver() {
                                field.requestCompute();
                            });
                            Object.assign(field, {
                                compute: () => {
                                    field.computing = true;
                                    field.computeOnNeed = false;
                                    updateFields(record, {
                                        [name]: fieldDefinition.compute.call(proxy2),
                                    });
                                    field.computing = false;
                                },
                                requestCompute: ({ force = false } = {}) => {
                                    if (Record.UPDATE !== 0 && !force) {
                                        Record.ADD_QUEUE(field, "compute");
                                    } else {
                                        if (field.eager || field.computeInNeed) {
                                            field.compute();
                                        } else {
                                            field.computeOnNeed = true;
                                        }
                                    }
                                },
                            });
                        }
                        if (fieldDefinition.sort) {
                            if (!fieldDefinition.eager) {
                                onChange(recordProxy, name, () => {
                                    if (field.sorting) {
                                        /**
                                         * Use a reactive to reset the inNeed flag when there is a
                                         * change. This assumes if another reactive is still observing
                                         * the value, its own callback will reset the flag to true
                                         * through the proxy getters.
                                         */
                                        field.sortInNeed = false;
                                    }
                                });
                                // reset flags triggered by registering onChange
                                field.computeInNeed = false;
                                field.sortInNeed = false;
                            }
                            const proxy2 = reactive(recordProxy, function sortObserver() {
                                field.requestSort();
                            });
                            Object.assign(field, {
                                sort: () => {
                                    field.sortOnNeed = false;
                                    field.sorting = true;
                                    sortRecordList(
                                        proxy2._fields.get(name).value._proxy,
                                        fieldDefinition.sort.bind(proxy2)
                                    );
                                    field.sorting = false;
                                },
                                requestSort: ({ force } = {}) => {
                                    if (Record.UPDATE !== 0 && !force) {
                                        Record.ADD_QUEUE(field, "sort");
                                    } else {
                                        if (field.eager || field.sortInNeed) {
                                            field.sort();
                                        } else {
                                            field.sortOnNeed = true;
                                        }
                                    }
                                },
                            });
                        }
                        if (fieldDefinition.onUpdate) {
                            /** @type {Function} */
                            let observe;
                            Object.assign(field, {
                                onUpdate: () => {
                                    /**
                                     * Forward internal proxy for performance as onUpdate does not
                                     * need reactive (observe is called separately).
                                     */
                                    fieldDefinition.onUpdate.call(record._proxyInternal);
                                    observe?.();
                                },
                            });
                            Record._onChange(recordProxy, name, (obs) => {
                                observe = obs;
                                if (Record.UPDATE !== 0) {
                                    Record.ADD_QUEUE(field, "onUpdate");
                                } else {
                                    field.onUpdate();
                                }
                            });
                        }
                    }
                    return recordProxy;
                }
            },
        }[OgClass.name];
        Object.assign(Model, {
            Class,
            env,
            records: reactive({}),
            _fields: new Map(),
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
            Model._fields.set(name, { [IS_FIELD_SYM]: true, [SYM]: true, ...val[1] });
        }
    }
    // Sync inverse fields
    for (const Model of Object.values(Models)) {
        for (const [name, fieldDefinition] of Model._fields) {
            if (!Record.isRelation(fieldDefinition)) {
                continue;
            }
            const { targetModel, inverse } = fieldDefinition;
            if (targetModel && !Models[targetModel]) {
                throw new Error(`No target model ${targetModel} exists`);
            }
            if (inverse) {
                const rel2 = Models[targetModel]._fields.get(inverse);
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
                fieldDefinition.eager = true;
                rel2.eager = true;
            }
        }
    }
    /**
     * store/_rawStore are assigned on models at next step, but they are
     * required on Store model to make the initial store insert.
     */
    Object.assign(res.store.Store, { store: res.store, _rawStore: res.store });
    // Make true store (as a model)
    res.store = toRaw(res.store.Store.insert())._raw;
    for (const Model of Object.values(Models)) {
        Model._rawStore = res.store;
        Model.store = res.store._proxy;
        res.store._proxy[Model.name] = Model;
    }
    Object.assign(res.store, { Models, storeReady: true });
    return res.store._proxy;
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
    data = new Map();
    /** @param {RecordList} list */
    add(list) {
        const record = list.owner;
        if (!this.data.has(record.localId)) {
            this.data.set(record.localId, new Map());
        }
        const use = this.data.get(record.localId);
        if (!use.get(list.name)) {
            use.set(list.name, 0);
        }
        use.set(list.name, use.get(list.name) + 1);
    }
    /** @param {RecordList} list */
    delete(list) {
        const record = list.owner;
        if (!this.data.has(record.localId)) {
            return;
        }
        const use = this.data.get(record.localId);
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
        return this.owner.Model._fields.get(this.name);
    }

    constructor() {
        super();
        const recordList = this;
        recordList._raw = recordList;
        const recordListProxyInternal = new Proxy(recordList, {
            /** @param {RecordList<R>} receiver */
            get(recordList, name, recordListFullProxy) {
                recordListFullProxy = recordList._downgradeProxy(recordListFullProxy);
                if (
                    typeof name === "symbol" ||
                    Object.keys(recordList).includes(name) ||
                    Object.prototype.hasOwnProperty.call(recordList.constructor.prototype, name)
                ) {
                    return Reflect.get(recordList, name, recordListFullProxy);
                }
                if (recordList.field?.compute && !recordList.field.eager) {
                    recordList.field.computeInNeed = true;
                    if (recordList.field.computeOnNeed) {
                        recordList.field.compute();
                    }
                }
                if (name === "length") {
                    return recordListFullProxy.data.length;
                }
                if (recordList.field?.sort && !recordList.field.eager) {
                    recordList.field.sortInNeed = true;
                    if (recordList.field.sortOnNeed) {
                        recordList.field.sort();
                    }
                }
                if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                    // support for "array[index]" syntax
                    const index = parseInt(name);
                    return recordListFullProxy.store.recordByLocalId.get(
                        recordListFullProxy.data[index]
                    );
                }
                // Attempt an unimplemented array method call
                const array = [
                    ...recordList._proxyInternal[Symbol.iterator].call(recordListFullProxy),
                ];
                return array[name]?.bind(array);
            },
            /** @param {RecordList<R>} recordListProxy */
            set(recordList, name, val, recordListProxy) {
                return Record.MAKE_UPDATE(function recordListSet() {
                    if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                        // support for "array[index] = r3" syntax
                        const index = parseInt(name);
                        recordList._insert(val, function recordListSet_Insert(newRecord) {
                            const oldRecord = toRaw(recordList.store.recordByLocalId).get(
                                recordList.data[index]
                            );
                            if (oldRecord && oldRecord.notEq(newRecord)) {
                                oldRecord.__uses__.delete(recordList);
                            }
                            Record.ADD_QUEUE(recordList.field, "onDelete", oldRecord);
                            const { inverse } = recordList.fieldDefinition;
                            if (inverse) {
                                oldRecord._fields.get(inverse).value.delete(recordList);
                            }
                            recordListProxy.data[index] = newRecord?.localId;
                            if (newRecord) {
                                newRecord.__uses__.add(recordList);
                                Record.ADD_QUEUE(recordList.field, "onAdd", newRecord);
                                const { inverse } = recordList.fieldDefinition;
                                if (inverse) {
                                    newRecord._fields.get(inverse).value.add(recordList);
                                }
                            }
                        });
                    } else if (name === "length") {
                        const newLength = parseInt(val);
                        if (newLength !== recordList.data.length) {
                            if (newLength < recordList.data.length) {
                                recordList.splice.call(
                                    recordListProxy,
                                    newLength,
                                    recordList.length - newLength
                                );
                            }
                            recordListProxy.data.length = newLength;
                        }
                    } else {
                        return Reflect.set(recordList, name, val, recordListProxy);
                    }
                    return true;
                });
            },
        });
        recordList._proxyInternal = recordListProxyInternal;
        recordList._proxy = reactive(recordListProxyInternal);
        return recordList;
    }

    /**
     * The internal reactive is only necessary to trigger outer reactives when
     * writing on it. As it has no callback, reading through it has no effect,
     * except slowing down performance and complexifying the stack.
     */
    _downgradeProxy(fullProxy) {
        return this._proxy === fullProxy ? this._proxyInternal : fullProxy;
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
        const recordList = this;
        const { inverse } = recordList.fieldDefinition;
        if (inverse && inv) {
            // special command to call _addNoinv/_deleteNoInv, to prevent infinite loop
            val[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", recordList.owner]];
        }
        /** @type {R} */
        let newRecordProxy;
        if (!Record.isRecord(val)) {
            const { targetModel } = recordList.fieldDefinition;
            newRecordProxy = recordList.store[targetModel].preinsert(val);
        } else {
            newRecordProxy = val;
        }
        const newRecord = toRaw(newRecordProxy)._raw;
        fn?.(newRecord);
        if (!Record.isRecord(val)) {
            // was preinserted, fully insert now
            const { targetModel } = recordList.fieldDefinition;
            recordList.store[targetModel].insert(val);
        }
        return newRecord;
    }
    /** @param {R[]|any[]} data */
    assign(data) {
        const recordList = toRaw(this)._raw;
        return Record.MAKE_UPDATE(function recordListAssign() {
            /** @type {Record[]|Set<Record>|RecordList<Record|any[]>} */
            const collection = Record.isRecord(data) ? [data] : data;
            // data and collection could be same record list,
            // save before clear to not push mutated recordlist that is empty
            const vals = [...collection];
            const oldRecords = recordList._proxyInternal.slice
                .call(recordList._proxy)
                .map((recordProxy) => toRaw(recordProxy)._raw);
            const newRecords = vals.map((val) =>
                recordList._insert(val, function recordListAssignInsert(record) {
                    if (record.notIn(oldRecords)) {
                        record.__uses__.add(recordList);
                        Record.ADD_QUEUE(recordList.field, "onAdd", record);
                    }
                })
            );
            const inverse = recordList.fieldDefinition.inverse;
            for (const oldRecord of oldRecords) {
                if (oldRecord.notIn(newRecords)) {
                    oldRecord.__uses__.delete(recordList);
                    Record.ADD_QUEUE(recordList.field, "onDelete", oldRecord);
                    if (inverse) {
                        oldRecord._fields.get(inverse).value.delete(recordList.owner);
                    }
                }
            }
            recordList._proxy.data = newRecords.map((newRecord) => newRecord.localId);
        });
    }
    /** @param {R[]} records */
    push(...records) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._downgradeProxy(this);
        return Record.MAKE_UPDATE(function recordListPush() {
            for (const val of records) {
                const record = recordList._insert(val, function recordListPushInsert(record) {
                    recordList._proxy.data.push(record.localId);
                    record.__uses__.add(recordList);
                });
                Record.ADD_QUEUE(recordList.field, "onAdd", record);
                const { inverse } = recordList.fieldDefinition;
                if (inverse) {
                    record._fields.get(inverse).value.add(recordList.owner);
                }
            }
            return recordListFullProxy.data.length;
        });
    }
    /** @returns {R} */
    pop() {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._downgradeProxy(this);
        return Record.MAKE_UPDATE(function recordListPop() {
            /** @type {R} */
            const oldRecordProxy = recordListFullProxy.at(-1);
            if (oldRecordProxy) {
                recordList.splice.call(recordListFullProxy, recordListFullProxy.length - 1, 1);
            }
            return oldRecordProxy;
        });
    }
    /** @returns {R} */
    shift() {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._downgradeProxy(this);
        return Record.MAKE_UPDATE(function recordListShift() {
            const recordProxy = recordListFullProxy.store.recordByLocalId.get(
                recordListFullProxy.data.shift()
            );
            if (!recordProxy) {
                return;
            }
            const record = toRaw(recordProxy)._raw;
            record.__uses__.delete(recordList);
            Record.ADD_QUEUE(recordList.field, "onDelete", record);
            const { inverse } = recordList.fieldDefinition;
            if (inverse) {
                record._fields.get(inverse).value.delete(recordList.owner);
            }
            return recordProxy;
        });
    }
    /** @param {R[]} records */
    unshift(...records) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._downgradeProxy(this);
        return Record.MAKE_UPDATE(function recordListUnshift() {
            for (let i = records.length - 1; i >= 0; i--) {
                const record = recordList._insert(records[i], (record) => {
                    recordList._proxy.data.unshift(record.localId);
                    record.__uses__.add(recordList);
                });
                Record.ADD_QUEUE(recordList.field, "onAdd", record);
                const { inverse } = recordList.fieldDefinition;
                if (inverse) {
                    record._fields.get(inverse).value.add(recordList.owner);
                }
            }
            return recordListFullProxy.data.length;
        });
    }
    /** @param {R} recordProxy */
    indexOf(recordProxy) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._downgradeProxy(this);
        return recordListFullProxy.data.indexOf(toRaw(recordProxy)?._raw.localId);
    }
    /**
     * @param {number} [start]
     * @param {number} [deleteCount]
     * @param {...R} [newRecordsProxy]
     */
    splice(start, deleteCount, ...newRecordsProxy) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._downgradeProxy(this);
        return Record.MAKE_UPDATE(function recordListSplice() {
            const oldRecordsProxy = recordList._proxyInternal.slice.call(
                recordListFullProxy,
                start,
                start + deleteCount
            );
            const list = recordListFullProxy.data.slice(); // splice on copy of list so that reactive observers not triggered while splicing
            list.splice(
                start,
                deleteCount,
                ...newRecordsProxy.map((newRecordProxy) => toRaw(newRecordProxy)._raw.localId)
            );
            recordList._proxy.data = list;
            for (const oldRecordProxy of oldRecordsProxy) {
                const oldRecord = toRaw(oldRecordProxy)._raw;
                oldRecord.__uses__.delete(recordList);
                Record.ADD_QUEUE(recordList.field, "onDelete", oldRecord);
                const { inverse } = recordList.fieldDefinition;
                if (inverse) {
                    oldRecord._fields.get(inverse).value.delete(recordList.owner);
                }
            }
            for (const newRecordProxy of newRecordsProxy) {
                const newRecord = toRaw(newRecordProxy)._raw;
                newRecord.__uses__.add(recordList);
                Record.ADD_QUEUE(recordList.field, "onAdd", newRecord);
                const { inverse } = recordList.fieldDefinition;
                if (inverse) {
                    newRecord._fields.get(inverse).value.add(recordList.owner);
                }
            }
        });
    }
    /** @param {(a: R, b: R) => boolean} func */
    sort(func) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._downgradeProxy(this);
        return Record.MAKE_UPDATE(function recordListSort() {
            sortRecordList(recordListFullProxy, func);
            return recordListFullProxy;
        });
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._downgradeProxy(this);
        return recordListFullProxy.data
            .map((localId) => recordListFullProxy.store.recordByLocalId.get(localId))
            .concat(...collections.map((c) => [...c]));
    }
    /** @param {...R}  */
    add(...records) {
        const recordList = toRaw(this)._raw;
        return Record.MAKE_UPDATE(function recordListAdd() {
            if (RecordList.isOne(recordList)) {
                const last = records.at(-1);
                if (Record.isRecord(last) && recordList.data.includes(toRaw(last)._raw.localId)) {
                    return;
                }
                recordList._insert(last, function recordListAddInsertOne(record) {
                    if (record.localId !== recordList.data[0]) {
                        recordList.pop.call(recordList._proxy);
                        recordList.push.call(recordList._proxy, record);
                    }
                });
                return;
            }
            for (const val of records) {
                if (Record.isRecord(val) && recordList.data.includes(val.localId)) {
                    continue;
                }
                recordList._insert(val, function recordListAddInsertMany(record) {
                    if (recordList.data.indexOf(record.localId) === -1) {
                        recordList.push.call(recordList._proxy, record);
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
        const recordList = this;
        if (RecordList.isOne(recordList)) {
            const last = records.at(-1);
            if (Record.isRecord(last) && last.in(recordList)) {
                return;
            }
            const record = recordList._insert(
                last,
                function recordList_AddNoInvOneInsert(record) {
                    if (record.localId !== recordList.data[0]) {
                        const old = recordList._proxy.at(-1);
                        recordList._proxy.data.pop();
                        old?.__uses__.delete(recordList);
                        recordList._proxy.data.push(record.localId);
                        record.__uses__.add(recordList);
                    }
                },
                { inv: false }
            );
            Record.ADD_QUEUE(recordList.field, "onAdd", record);
            return;
        }
        for (const val of records) {
            if (Record.isRecord(val) && val.in(recordList)) {
                continue;
            }
            const record = recordList._insert(
                val,
                function recordList_AddNoInvManyInsert(record) {
                    if (recordList.data.indexOf(record.localId) === -1) {
                        recordList.push.call(recordList._proxy, record);
                        record.__uses__.add(recordList);
                    }
                },
                { inv: false }
            );
            Record.ADD_QUEUE(recordList.field, "onAdd", record);
        }
    }
    /** @param {...R}  */
    delete(...records) {
        const recordList = toRaw(this)._raw;
        return Record.MAKE_UPDATE(function recordListDelete() {
            for (const val of records) {
                recordList._insert(
                    val,
                    function recordListDelete_Insert(record) {
                        const index = recordList.data.indexOf(record.localId);
                        if (index !== -1) {
                            recordList.splice.call(recordList._proxy, index, 1);
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
        const recordList = this;
        for (const val of records) {
            const record = recordList._insert(
                val,
                function recordList_DeleteNoInv_Insert(record) {
                    const index = recordList.data.indexOf(record.localId);
                    if (index !== -1) {
                        recordList.splice.call(recordList._proxy, index, 1);
                        record.__uses__.delete(recordList);
                    }
                },
                { inv: false }
            );
            Record.ADD_QUEUE(recordList.field, "onDelete", record);
        }
    }
    clear() {
        const recordList = toRaw(this)._raw;
        return Record.MAKE_UPDATE(function recordListClear() {
            while (recordList.data.length > 0) {
                recordList.pop.call(recordList._proxy);
            }
        });
    }
    /** @yields {R} */
    *[Symbol.iterator]() {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._downgradeProxy(this);
        for (const localId of recordListFullProxy.data) {
            yield recordListFullProxy.store.recordByLocalId.get(localId);
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
 * @property {() => void} [sort] for sorted field, invoking this function (re-)sorts the field.
 * @property {boolean} [sorting] for sorted field, determines whether the field is sorting its value.
 * @property {() => void} [requestSort] on sorted field, calling this function makes a request to sort
 *   the field. This doesn't necessarily mean the field is immediately re-sorted: during an update cycle, this
 *   is put in the sort FS_QUEUE and will be invoked at end.
 * @property {boolean} [sortOnNeed] on lazy-sorted field, determines whether the field should be (re-)sorted
 *   when it's needed (i.e. accessed). Eager sorted fields are immediately re-sorted at end of update cycle,
 *   whereas lazy sorted fields wait extra for them being needed.
 * @property {boolean} [sortInNeed] on lazy sorted-fields, determines whether this field is needed (i.e. accessed).
 * @property {() => void} [onUpdate] function that contains functions to be called when the value of field
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
    static records;
    /** @type {import("models").Store} */
    static store;
    /** @type {RecordField[]} */
    static FC_QUEUE = []; // field-computes
    /** @type {RecordField[]} */
    static FS_QUEUE = []; // field-sorts
    /** @type {Array<{field: RecordField, records: Record[]}>} */
    static FA_QUEUE = []; // field-onadds
    /** @type {Array<{field: RecordField, records: Record[]}>} */
    static FD_QUEUE = []; // field-ondeletes
    /** @type {RecordField[]} */
    static FU_QUEUE = []; // field-onupdates
    /** @type {Function[]} */
    static RO_QUEUE = []; // record-onchanges
    /** @type {Record[]} */
    static RD_QUEUE = []; // record-deletes
    static UPDATE = 0;
    /** @param {() => any} fn */
    static MAKE_UPDATE(fn) {
        Record.UPDATE++;
        const res = fn();
        Record.UPDATE--;
        if (Record.UPDATE === 0) {
            // pretend an increased update cycle so that nothing in queue creates many small update cycles
            Record.UPDATE++;
            while (
                Record.FC_QUEUE.length > 0 ||
                Record.FS_QUEUE.length > 0 ||
                Record.FA_QUEUE.length > 0 ||
                Record.FD_QUEUE.length > 0 ||
                Record.FU_QUEUE.length > 0 ||
                Record.RO_QUEUE.length > 0 ||
                Record.RD_QUEUE.length > 0
            ) {
                const FC_QUEUE = [...Record.FC_QUEUE];
                const FS_QUEUE = [...Record.FS_QUEUE];
                const FA_QUEUE = [...Record.FA_QUEUE];
                const FD_QUEUE = [...Record.FD_QUEUE];
                const FU_QUEUE = [...Record.FU_QUEUE];
                const RO_QUEUE = [...Record.RO_QUEUE];
                const RD_QUEUE = [...Record.RD_QUEUE];
                Record.FC_QUEUE.length = 0;
                Record.FS_QUEUE.length = 0;
                Record.FA_QUEUE.length = 0;
                Record.FD_QUEUE.length = 0;
                Record.FU_QUEUE.length = 0;
                Record.RO_QUEUE.length = 0;
                Record.RD_QUEUE.length = 0;
                while (FC_QUEUE.length > 0) {
                    const field = FC_QUEUE.pop();
                    field.requestCompute({ force: true });
                }
                while (FS_QUEUE.length > 0) {
                    const field = FS_QUEUE.pop();
                    field.requestSort({ force: true });
                }
                while (FA_QUEUE.length > 0) {
                    const { field, records } = FA_QUEUE.pop();
                    const { onAdd } = field.value.fieldDefinition;
                    records.forEach((record) =>
                        onAdd?.call(field.value.owner._proxy, record._proxy)
                    );
                }
                while (FD_QUEUE.length > 0) {
                    const { field, records } = FD_QUEUE.pop();
                    const { onDelete } = field.value.fieldDefinition;
                    records.forEach((record) =>
                        onDelete?.call(field.value.owner._proxy, record._proxy)
                    );
                }
                while (FU_QUEUE.length > 0) {
                    const field = FU_QUEUE.pop();
                    field.onUpdate();
                }
                while (RO_QUEUE.length > 0) {
                    const cb = RO_QUEUE.pop();
                    cb();
                }
                while (RD_QUEUE.length > 0) {
                    const record = RD_QUEUE.pop();
                    // effectively delete the record
                    for (const name of record._fields.keys()) {
                        record[name] = undefined;
                    }
                    for (const [localId, names] of record.__uses__.data.entries()) {
                        for (const [name2, count] of names.entries()) {
                            const usingRecordProxy = toRaw(
                                record.Model._rawStore.recordByLocalId
                            ).get(localId);
                            if (!usingRecordProxy) {
                                // record already deleted, clean inverses
                                record.__uses__.data.delete(localId);
                                continue;
                            }
                            const usingRecordList =
                                toRaw(usingRecordProxy)._raw._fields.get(name2).value;
                            if (RecordList.isMany(usingRecordList)) {
                                for (let c = 0; c < count; c++) {
                                    usingRecordProxy[name2].delete(record);
                                }
                            } else {
                                usingRecordProxy[name2] = undefined;
                            }
                        }
                    }
                    delete record.Model.records[record.localId];
                    record.Model._rawStore.recordByLocalId.delete(record.localId);
                }
            }
            Record.UPDATE--;
        }
        return res;
    }
    /**
     * @param {RecordField|Record} fieldOrRecord
     * @param {"compute"|"sort"|"onAdd"|"onDelete"|"onUpdate"} type
     * @param {Record} [record] when field with onAdd/onDelete, the record being added or deleted
     */
    static ADD_QUEUE(fieldOrRecord, type, record) {
        if (Record.isRecord(fieldOrRecord)) {
            /** @type {Record} */
            const record = fieldOrRecord;
            if (type === "delete") {
                if (!Record.RD_QUEUE.includes(record)) {
                    Record.RD_QUEUE.push(record);
                }
            }
        } else {
            /** @type {RecordField} */
            const field = fieldOrRecord;
            const rawField = toRaw(field);
            if (type === "compute") {
                if (!Record.FC_QUEUE.some((f) => toRaw(f) === rawField)) {
                    Record.FC_QUEUE.push(field);
                }
            }
            if (type === "sort") {
                if (!rawField.value?.fieldDefinition.sort) {
                    return;
                }
                if (!Record.FS_QUEUE.some((f) => toRaw(f) === rawField)) {
                    Record.FS_QUEUE.push(field);
                }
            }
            if (type === "onAdd") {
                if (rawField.value?.fieldDefinition.sort) {
                    Record.ADD_QUEUE(fieldOrRecord, "sort");
                }
                if (!rawField.value?.fieldDefinition.onAdd) {
                    return;
                }
                const item = Record.FA_QUEUE.find((item) => toRaw(item.field) === rawField);
                if (!item) {
                    Record.FA_QUEUE.push({ field, records: [record] });
                } else {
                    if (!item.records.some((recordProxy) => recordProxy.eq(record))) {
                        item.records.push(record);
                    }
                }
            }
            if (type === "onDelete") {
                if (!rawField.value?.fieldDefinition.onDelete) {
                    return;
                }
                const item = Record.FD_QUEUE.find((item) => toRaw(item.field) === rawField);
                if (!item) {
                    Record.FD_QUEUE.push({ field, records: [record] });
                } else {
                    if (!item.records.some((recordProxy) => recordProxy.eq(record))) {
                        item.records.push(record);
                    }
                }
            }
            if (type === "onUpdate") {
                if (!Record.FU_QUEUE.some((f) => toRaw(f) === rawField)) {
                    Record.FU_QUEUE.push(field);
                }
            }
        }
    }
    static onChange(record, name, cb) {
        return Record._onChange(record, name, (observe) => {
            const fn = () => {
                observe();
                cb();
            };
            if (Record.UPDATE !== 0) {
                if (!Record.RO_QUEUE.some((f) => toRaw(f) === fn)) {
                    Record.RO_QUEUE.push(fn);
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
     * @returns {function} function to call to stop observing changes
     */
    static _onChange(record, key, callback) {
        let proxy;
        function _observe() {
            // access proxy[key] only once to avoid triggering reactive get() many times
            const val = proxy[key];
            if (typeof val === "object" && val !== null) {
                void Object.keys(val);
            }
            if (Array.isArray(val)) {
                void val.length;
                void toRaw(val).forEach.call(val, (i) => i);
            }
        }
        if (Array.isArray(key)) {
            for (const k of key) {
                Record._onChange(record, k, callback);
            }
            return;
        }
        let ready = true;
        proxy = reactive(record, () => {
            if (ready) {
                callback(_observe);
            }
        });
        _observe();
        return () => {
            ready = false;
        };
    }
    /**
     * Contains field definitions of the model:
     * - key : field name
     * - value: Value contains definition of field
     *
     * @type {Map<string, FieldDefinition>}
     */
    static _fields;
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
        const Model = toRaw(this);
        return this.records[Model.localId(data)];
    }
    static register() {
        modelRegistry.add(this.name, this);
    }
    static localId(data) {
        const Model = toRaw(this);
        let idStr;
        if (typeof data === "object" && data !== null) {
            idStr = Model._localId(Model.id, data);
        } else {
            idStr = data; // non-object data => single id
        }
        return `${Model.name},${idStr}`;
    }
    static _localId(expr, data, { brackets = false } = {}) {
        const Model = toRaw(this);
        if (!Array.isArray(expr)) {
            const fieldDefinition = Model._fields.get(expr);
            if (fieldDefinition) {
                if (RecordList.isMany(fieldDefinition)) {
                    throw new Error("Using a Record.Many() as id is not (yet) supported");
                }
                if (!Record.isRelation(fieldDefinition)) {
                    return data[expr];
                }
                if (Record.isCommand(data[expr])) {
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
            vals.push(Model._localId(expr[i], data, { brackets: true }));
        }
        let res = vals.join(expr[0] === OR_SYM ? " OR " : " AND ");
        if (brackets) {
            res = `(${res})`;
        }
        return res;
    }
    static _retrieveIdFromData(data) {
        const Model = toRaw(this);
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
        if (Model.id === undefined) {
            return res;
        }
        if (typeof Model.id === "string") {
            if (typeof data !== "object" || data === null) {
                return { [Model.id]: data }; // non-object data => single id
            }
            if (Record.isCommand(data[Model.id])) {
                // Note: only Record.one() is supported
                const [cmd, data2] = data[Model.id].at(-1);
                return Object.assign(res, {
                    [Model.id]:
                        cmd === "DELETE"
                            ? undefined
                            : cmd === "DELETE.noinv"
                            ? [["DELETE.noinv", data2]]
                            : cmd === "ADD.noinv"
                            ? [["ADD.noinv", data2]]
                            : data2,
                });
            }
            return { [Model.id]: data[Model.id] };
        }
        for (const expr of Model.id) {
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
        const Model = toRaw(this);
        return Record.MAKE_UPDATE(function RecordNew() {
            const recordProxy = new Model.Class();
            const record = toRaw(recordProxy)._raw;
            const ids = Model._retrieveIdFromData(data);
            for (const name in ids) {
                if (
                    ids[name] &&
                    !Record.isRecord(ids[name]) &&
                    !Record.isCommand(ids[name]) &&
                    Record.isRelation(Model._fields.get(name))
                ) {
                    // preinsert that record in relational field,
                    // as it is required to make current local id
                    ids[name] = Model._rawStore[Model._fields.get(name).targetModel].preinsert(
                        ids[name]
                    );
                }
            }
            Object.assign(record, { localId: Model.localId(ids) });
            Object.assign(recordProxy, { ...ids });
            Model.records[record.localId] = recordProxy;
            if (record.Model.name === "Store") {
                Object.assign(record, {
                    env: Model._rawStore.env,
                    recordByLocalId: Model._rawStore.recordByLocalId,
                });
            }
            Model._rawStore.recordByLocalId.set(record.localId, recordProxy);
            for (const field of record._fields.values()) {
                field.requestCompute?.();
                field.requestSort?.();
            }
            return recordProxy;
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
        const ModelFullProxy = this;
        const Model = toRaw(ModelFullProxy);
        return Record.MAKE_UPDATE(function RecordInsert() {
            const isMulti = Array.isArray(data);
            if (!isMulti) {
                data = [data];
            }
            const oldTrusted = Record.trusted;
            Record.trusted = options.html ?? Record.trusted;
            const res = data.map(function RecordInsertMap(d) {
                return Model._insert.call(ModelFullProxy, d, options);
            });
            Record.trusted = oldTrusted;
            if (!isMulti) {
                return res[0];
            }
            return res;
        });
    }
    /** @returns {Record} */
    static _insert(data) {
        const ModelFullProxy = this;
        const Model = toRaw(ModelFullProxy);
        const recordFullProxy = Model.preinsert.call(ModelFullProxy, data);
        const record = toRaw(recordFullProxy)._raw;
        record.update.call(record._proxy, data);
        return recordFullProxy;
    }
    /**
     * @param {Object} data
     * @returns {Record}
     */
    static preinsert(data) {
        const ModelFullProxy = this;
        const Model = toRaw(ModelFullProxy);
        return Model.get.call(ModelFullProxy, data) ?? Model.new(data);
    }
    static isCommand(data) {
        return ["ADD", "DELETE", "ADD.noinv", "DELETE.noinv"].includes(data?.[0]?.[0]);
    }

    /**
     * Raw relational values of the record, each of which contains object id(s)
     * rather than the record(s). This allows data in store and models being normalized,
     * which eases handling relations notably in when a record gets deleted.
     *
     * @type {Map<string, RecordField>}
     */
    _fields = new Map();
    __uses__ = markRaw(new RecordUses());
    get _store() {
        return toRaw(this)._raw.Model._rawStore._proxy;
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
        const record = toRaw(this)._raw;
        return Record.MAKE_UPDATE(function recordUpdate() {
            if (typeof data === "object" && data !== null) {
                updateFields(record, data);
            } else {
                // update on single-id data
                updateFields(record, { [record.Model.id]: data });
            }
        });
    }

    delete() {
        const record = toRaw(this)._raw;
        return Record.MAKE_UPDATE(function recordDelete() {
            Record.ADD_QUEUE(record, "delete");
        });
    }

    /** @param {Record} record */
    eq(record) {
        return toRaw(this)._raw === toRaw(record)?._raw;
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
        return collection.some((record) => toRaw(record)._raw.eq(this));
    }

    /** @param {Record[]|RecordList} collection */
    notIn(collection) {
        return !this.in(collection);
    }

    toData() {
        const recordProxy = this;
        const record = toRaw(recordProxy)._raw;
        const data = { ...recordProxy };
        for (const [name, { value }] of record._fields) {
            if (RecordList.isMany(value)) {
                data[name] = value.map((recordProxy) => {
                    const record = toRaw(recordProxy)._raw;
                    return record.toIdData.call(record._proxyInternal);
                });
            } else if (RecordList.isOne(value)) {
                const record = toRaw(value[0])?._raw;
                data[name] = record?.toIdData.call(record._proxyInternal);
            } else {
                data[name] = recordProxy[name]; // Record.attr()
            }
        }
        delete data._fields;
        delete data._proxy;
        delete data._proxyInternal;
        delete data._proxyUsed;
        delete data._raw;
        delete data.Model;
        delete data._updateFields;
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

    /**
     * The internal reactive is only necessary to trigger outer reactives when
     * writing on it. As it has no callback, reading through it has no effect,
     * except slowing down performance and complexifying the stack.
     */
    _downgradeProxy(fullProxy) {
        return this._proxy === fullProxy ? this._proxyInternal : fullProxy;
    }
}

Record.register();

export class BaseStore extends Record {
    storeReady = false;
    /**
     * @param {string} localId
     * @returns {Record}
     */
    get(localId) {
        return this.recordByLocalId.get(localId);
    }
}
