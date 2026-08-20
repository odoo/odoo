import { isRecord, untrackFunctions } from "./misc";
import { RecordListInternal } from "./record_list_internal";

import { proxy, toRaw } from "@odoo/owl";

/** @typedef {import("./record").Record} Record */

/** * @template {Record} R */
export class RecordList extends Array {
    /** @type {import("models").Store} */
    _store;
    /** @type {Record[]} raw */
    data = [];
    /** @type {this} */
    _raw;
    /** @type {this} */
    _proxyInternal;
    /** @type {this} */
    _proxy;
    _ = new RecordListInternal();

    constructor() {
        super();
        const recordList = this;
        recordList._raw = recordList;
        const recordListProxyInternal = new Proxy(recordList, {
            /** @param {RecordList<R>} receiver */
            get(recordList, name, recordListFullProxy) {
                if (name === "data" && !recordList._.gettingField) {
                    recordList._.gettingField = true;
                    try {
                        return recordList._proxy.data;
                    } finally {
                        recordList._.gettingField = false;
                    }
                }
                if (
                    recordList._.gettingField ||
                    typeof name === "symbol" ||
                    Object.keys(recordList).includes(name) ||
                    Object.prototype.hasOwnProperty.call(recordList.constructor.prototype, name)
                ) {
                    let res = Reflect.get(...arguments);
                    if (typeof res === "function") {
                        res = res.bind(recordListFullProxy);
                    }
                    return res;
                }
                if (recordList._.isComputeField() && !recordList._.isEager()) {
                    recordList._.setComputeInNeed();
                    if (recordList._.isComputeOnNeed()) {
                        recordList._.computeField();
                    }
                }
                if (name === "length") {
                    return recordListFullProxy.data.length;
                }
                if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                    // support for "array[index]" syntax
                    const index = parseInt(name);
                    return recordListFullProxy.data[index]?._proxy;
                }
                // Attempt an unimplemented array method call
                const array = [...recordList[Symbol.iterator].call(recordListFullProxy)];
                return array[name]?.bind(array);
            },
            /** @param {RecordList<R>} recordListProxy */
            set(recordList, name, val, recordListProxy) {
                const store = recordList._store;
                return store.MAKE_UPDATE(function recordListSet() {
                    if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                        // support for "array[index] = r3" syntax
                        const index = parseInt(name);
                        recordList._.insert(
                            recordList,
                            val,
                            function recordListSet_Insert(newRecord) {
                                const oldRecord = recordList.data[index];
                                recordListProxy.data[index] = newRecord;
                                if (oldRecord && oldRecord.notEq(newRecord)) {
                                    oldRecord._.uses.delete(recordList);
                                }
                                store._.ADD_QUEUE(
                                    "onDelete",
                                    recordList._.owner,
                                    recordList._.name,
                                    oldRecord
                                );
                                const inverse = recordList._.getInverse();
                                if (inverse) {
                                    store._.updateFields(oldRecord, {
                                        [inverse]: [["DELETE", recordList._.owner]],
                                    });
                                }
                                if (newRecord) {
                                    newRecord._.uses.add(recordList);
                                    store._.ADD_QUEUE(
                                        "onAdd",
                                        recordList._.owner,
                                        recordList._.name,
                                        newRecord
                                    );
                                    if (inverse) {
                                        store._.updateFields(newRecord, {
                                            [inverse]: [["ADD", recordList._.owner]],
                                        });
                                    }
                                }
                            }
                        );
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
                            recordList._.syncLength(recordList);
                        }
                    } else {
                        return Reflect.set(recordList, name, val, recordListProxy);
                    }
                    return true;
                });
            },
        });
        recordList._proxyInternal = recordListProxyInternal;
        recordList._proxy = proxy(recordListProxyInternal);
        return recordList;
    }
    /** @param {R[]} records */
    push(...records) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListPush() {
            const inverse = recordList._.getInverse();
            for (const val of records) {
                const record = recordList._.insert(
                    recordList,
                    val,
                    function recordListPushInsert(record) {
                        recordList._proxy.data.push(record);
                        recordList._.syncLength(recordList);
                        record._.uses.add(recordList);
                    }
                );
                store._.ADD_QUEUE("onAdd", recordList._.owner, recordList._.name, record);
                if (inverse) {
                    store._.updateFields(record, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
            return recordListFullProxy.data.length;
        });
    }
    /** @returns {R} */
    pop() {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = this;
        const store = recordList._store;
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
        const recordListFullProxy = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListShift() {
            const record = recordListFullProxy.data.shift();
            recordList._.syncLength(recordList);
            if (!record) {
                return;
            }
            record._.uses.delete(recordList);
            store._.ADD_QUEUE("onDelete", recordList._.owner, recordList._.name, record);
            const inverse = recordList._.getInverse();
            if (inverse) {
                store._.updateFields(record, { [inverse]: [["DELETE", recordList._.owner]] });
            }
            return record._proxy;
        });
    }
    /** @param {R[]} records */
    unshift(...records) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListUnshift() {
            const inverse = recordList._.getInverse();
            for (let i = records.length - 1; i >= 0; i--) {
                const record = recordList._.insert(recordList, records[i], (record) => {
                    recordList._proxy.data.unshift(record);
                    recordList._.syncLength(recordList);
                    record._.uses.add(recordList);
                });
                store._.ADD_QUEUE("onAdd", recordList._.owner, recordList._.name, record);
                if (inverse) {
                    store._.updateFields(record, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
            return recordListFullProxy.data.length;
        });
    }
    /** @param {R} recordProxy */
    indexOf(recordProxy) {
        const recordListFullProxy = this;
        return recordListFullProxy.data.indexOf(recordProxy?._raw);
    }
    /**
     * @param {number} [start]
     * @param {number} [deleteCount]
     * @param {...R} [newRecordsProxy]
     */
    splice(start, deleteCount, ...newRecordsProxy) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListSplice() {
            const oldRecords = recordList.data.slice(start, start + deleteCount);
            const list = recordListFullProxy.data.slice(); // splice on copy of list so that reactive observers not triggered while splicing
            list.splice(
                start,
                deleteCount,
                ...newRecordsProxy.map((recordProxy) => recordProxy._raw)
            );
            if (recordList._.isOne() && start === 0 && deleteCount === 1) {
                // avoid replacing whole list, to avoid triggering observers too much
                if (list.length === 0) {
                    recordList._proxy.data.pop();
                } else {
                    recordList._proxy.data[0] = list[0];
                }
            } else {
                recordList._proxy.data = list;
            }
            recordList._.syncLength(recordList);
            const inverse = recordList._.getInverse();
            for (const oldRecord of oldRecords) {
                oldRecord._.uses.delete(recordList);
                store._.ADD_QUEUE("onDelete", recordList._.owner, recordList._.name, oldRecord);
                if (inverse) {
                    store._.updateFields(oldRecord, {
                        [inverse]: [["DELETE", recordList._.owner]],
                    });
                }
            }
            for (const newRecordProxy of newRecordsProxy) {
                const newRecord = newRecordProxy._raw;
                newRecord._.uses.add(recordList);
                store._.ADD_QUEUE("onAdd", recordList._.owner, recordList._.name, newRecord);
                if (inverse) {
                    store._.updateFields(newRecord, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
        });
    }
    /** @param {(a: R, b: R) => boolean} func */
    sort(func) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListSort() {
            recordList._store._.sortRecordList(recordListFullProxy, func);
            return recordListFullProxy;
        });
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        const recordListFullProxy = this;
        return recordListFullProxy.data
            .map((record) => record._proxy)
            .concat(...collections.map((c) => [...c]));
    }
    /**
     * @param {...R}
     * @returns {R|R[]} the added record(s)
     */
    add(...records) {
        const recordList = toRaw(this)._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListAdd() {
            if (recordList._.isOne()) {
                const last = records.at(-1);
                if (isRecord(last) && recordList.data.includes(last._raw)) {
                    return last;
                }
                return recordList._.insert(
                    recordList,
                    last,
                    function recordListAddInsertOne(record) {
                        if (record !== recordList.data[0]) {
                            recordList.splice.call(recordList._proxy, 0, 1, record._proxy);
                        }
                    }
                );
            }
            const res = [];
            for (const val of records) {
                if (isRecord(val) && recordList.data.includes(val._raw)) {
                    continue;
                }
                const rec = recordList._.insert(
                    recordList,
                    val,
                    function recordListAddInsertMany(record) {
                        if (recordList.data.indexOf(record) === -1) {
                            recordList.push.call(recordList._proxy, record);
                        }
                    }
                );
                res.push(rec);
            }
            return res.length === 1 ? res[0] : res;
        });
    }
    /** @param {...R}  */
    delete(...records) {
        const recordList = toRaw(this)._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListDelete() {
            for (const val of records) {
                recordList._.insert(
                    recordList,
                    val,
                    function recordListDelete_Insert(record) {
                        const index = recordList.data.indexOf(record);
                        if (index !== -1) {
                            recordList.splice.call(recordList._proxy, index, 1);
                        }
                    },
                    { mode: "DELETE" }
                );
            }
        });
    }
    clear() {
        const recordList = toRaw(this)._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListClear() {
            while (recordList.data.length > 0) {
                recordList.pop.call(recordList._proxy);
            }
        });
    }
    /** @yields {R} */
    *[Symbol.iterator]() {
        const recordListFullProxy = this;
        for (const record of recordListFullProxy.data) {
            yield record._proxy;
        }
    }
    /** @param {number} index */
    at(index) {
        // this custom implement of "at" is slightly faster than auto-calling unimplement array method
        const recordListFullProxy = this;
        return recordListFullProxy.data.at(index)?._proxy;
    }
}

untrackFunctions(RecordList.prototype, [
    "add",
    "clear",
    "delete",
    "pop",
    "push",
    "shift",
    "splice",
    "unshift",
]);
