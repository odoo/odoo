import { reactive, toRaw } from "@odoo/owl";
import { isMany, isOne, isRecord } from "./misc";

/** * @template {Record} R */
export class RecordList extends Array {
    static isOne(list) {
        return isOne(list);
    }
    static isMany(list) {
        return isMany(list);
    }
    /** @type {Record} */
    owner;
    /** @type {string} */
    name;
    /** @type {import("models").Store} */
    store;
    /** @type {string[]} */
    data = [];
    /** @type {this} */
    _raw;
    /** @type {this} */
    _proxyInternal;
    /** @type {this} */
    _proxy;

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
                const store = recordList.store;
                return store.MAKE_UPDATE(function recordListSet() {
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
                            store.ADD_QUEUE(recordList.field, "onDelete", oldRecord);
                            const { inverse } = recordList.fieldDefinition;
                            if (inverse) {
                                oldRecord._fields.get(inverse).value.delete(recordList);
                            }
                            recordListProxy.data[index] = newRecord?.localId;
                            if (newRecord) {
                                newRecord.__uses__.add(recordList);
                                store.ADD_QUEUE(recordList.field, "onAdd", newRecord);
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
        if (!isRecord(val)) {
            const { targetModel } = recordList.fieldDefinition;
            newRecordProxy = recordList.store[targetModel].preinsert(val);
        } else {
            newRecordProxy = val;
        }
        const newRecord = toRaw(newRecordProxy)._raw;
        fn?.(newRecord);
        if (!isRecord(val)) {
            // was preinserted, fully insert now
            const { targetModel } = recordList.fieldDefinition;
            recordList.store[targetModel].insert(val);
        }
        return newRecord;
    }
    /** @param {R[]|any[]} data */
    assign(data) {
        const recordList = toRaw(this)._raw;
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListAssign() {
            /** @type {Record[]|Set<Record>|RecordList<Record|any[]>} */
            const collection = isRecord(data) ? [data] : data;
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
                        store.ADD_QUEUE(recordList.field, "onAdd", record);
                    }
                })
            );
            const inverse = recordList.fieldDefinition.inverse;
            for (const oldRecord of oldRecords) {
                if (oldRecord.notIn(newRecords)) {
                    oldRecord.__uses__.delete(recordList);
                    store.ADD_QUEUE(recordList.field, "onDelete", oldRecord);
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
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListPush() {
            for (const val of records) {
                const record = recordList._insert(val, function recordListPushInsert(record) {
                    recordList._proxy.data.push(record.localId);
                    record.__uses__.add(recordList);
                });
                store.ADD_QUEUE(recordList.field, "onAdd", record);
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
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListPop() {
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
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListShift() {
            const recordProxy = recordListFullProxy.store.recordByLocalId.get(
                recordListFullProxy.data.shift()
            );
            if (!recordProxy) {
                return;
            }
            const record = toRaw(recordProxy)._raw;
            record.__uses__.delete(recordList);
            store.ADD_QUEUE(recordList.field, "onDelete", record);
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
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListUnshift() {
            for (let i = records.length - 1; i >= 0; i--) {
                const record = recordList._insert(records[i], (record) => {
                    recordList._proxy.data.unshift(record.localId);
                    record.__uses__.add(recordList);
                });
                store.ADD_QUEUE(recordList.field, "onAdd", record);
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
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListSplice() {
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
                store.ADD_QUEUE(recordList.field, "onDelete", oldRecord);
                const { inverse } = recordList.fieldDefinition;
                if (inverse) {
                    oldRecord._fields.get(inverse).value.delete(recordList.owner);
                }
            }
            for (const newRecordProxy of newRecordsProxy) {
                const newRecord = toRaw(newRecordProxy)._raw;
                newRecord.__uses__.add(recordList);
                store.ADD_QUEUE(recordList.field, "onAdd", newRecord);
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
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListSort() {
            recordList.store.sortRecordList(recordListFullProxy, func);
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
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListAdd() {
            if (isOne(recordList)) {
                const last = records.at(-1);
                if (isRecord(last) && recordList.data.includes(toRaw(last)._raw.localId)) {
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
                if (isRecord(val) && recordList.data.includes(val.localId)) {
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
        const store = recordList.store;
        if (isOne(recordList)) {
            const last = records.at(-1);
            if (isRecord(last) && last.in(recordList)) {
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
            store.ADD_QUEUE(recordList.field, "onAdd", record);
            return;
        }
        for (const val of records) {
            if (isRecord(val) && val.in(recordList)) {
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
            store.ADD_QUEUE(recordList.field, "onAdd", record);
        }
    }
    /** @param {...R}  */
    delete(...records) {
        const recordList = toRaw(this)._raw;
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListDelete() {
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
        const store = recordList.store;
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
            store.ADD_QUEUE(recordList.field, "onDelete", record);
        }
    }
    clear() {
        const recordList = toRaw(this)._raw;
        const store = recordList.store;
        return store.MAKE_UPDATE(function recordListClear() {
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
