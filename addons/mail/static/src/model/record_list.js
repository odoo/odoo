import { markRaw, reactive, toRaw } from "@odoo/owl";
import { isRecord } from "./misc";

/** @param {RecordList} reclist */
function getInverse(reclist) {
    return reclist._.owner.Model._.fieldsInverse.get(reclist._.name);
}

/** @param {RecordList} reclist */
function getTargetModel(reclist) {
    return reclist._.owner.Model._.fieldsTargetModel.get(reclist._.name);
}

/** @param {RecordList} reclist */
function isComputeField(reclist) {
    return reclist._.owner.Model._.fieldsCompute.get(reclist._.name);
}

/** @param {RecordList} reclist */
function isSortField(reclist) {
    return reclist._.owner.Model._.fieldsSort.get(reclist._.name);
}

/** @param {RecordList} reclist */
function isEager(reclist) {
    return reclist._.owner.Model._.fieldsEager.get(reclist._.name);
}

/** @param {RecordList} reclist */
function setComputeInNeed(reclist) {
    reclist._.owner._.fieldsComputeInNeed.set(reclist._.name, true);
}

/** @param {RecordList} reclist */
function setSortInNeed(reclist) {
    reclist._.owner._.fieldsSortInNeed.set(reclist._.name, true);
}

/** @param {RecordList} reclist */
function isComputeOnNeed(reclist) {
    return reclist._.owner._.fieldsComputeOnNeed.get(reclist._.name);
}

/** @param {RecordList} reclist */
function isSortOnNeed(reclist) {
    return reclist._.owner._.fieldsSortOnNeed.get(reclist._.name);
}

/** @param {RecordList} reclist */
function computeField(reclist) {
    reclist._.owner._.compute(reclist._.owner, reclist._.name);
}

/** @param {RecordList} reclist */
function sortField(reclist) {
    reclist._.owner._.sort(reclist._.owner, reclist._.name);
}

/** @param {RecordList} reclist */
function isOne(reclist) {
    return reclist._.owner.Model._.fieldsOne.get(reclist._.name);
}

export class RecordListInternal {
    /** @type {string} */
    name;
    /** @type {Record} */
    owner;

    /**
     * Version of add() that does not update the inverse.
     * This is internally called when inserting (with intent to add)
     * on relational field with inverse, to prevent infinite loops.
     *
     * @param {RecordList} recordList
     * @param {...Record}
     */
    addNoinv(recordList, ...records) {
        const self = this;
        const store = recordList._store;
        if (isOne(recordList)) {
            const last = records.at(-1);
            if (isRecord(last) && last.in(recordList)) {
                return;
            }
            const record = self.insert(
                recordList,
                last,
                function recordList_AddNoInvOneInsert(record) {
                    if (record.localId !== recordList.data[0]) {
                        const old = recordList._proxy.at(-1);
                        recordList._proxy.data.pop();
                        old?._.uses.delete(recordList);
                        recordList._proxy.data.push(record.localId);
                        self.syncLength(recordList);
                        record._.uses.add(recordList);
                    }
                },
                { inv: false }
            );
            store._.ADD_QUEUE("onAdd", self.owner, self.name, record);
            return;
        }
        for (const val of records) {
            if (isRecord(val) && val.in(recordList)) {
                continue;
            }
            const record = self.insert(
                recordList,
                val,
                function recordList_AddNoInvManyInsert(record) {
                    if (recordList.data.indexOf(record.localId) === -1) {
                        recordList._proxy.data.push(record.localId);
                        self.syncLength(recordList);
                        record._.uses.add(recordList);
                    }
                },
                { inv: false }
            );
            store._.ADD_QUEUE("onAdd", self.owner, self.name, record);
        }
    }
    /** @param {R[]|any[]} data */
    assign(recordList, data) {
        const self = this;
        const store = recordList._store;
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
                self.insert(recordList, val, function recordListAssignInsert(record) {
                    if (record.notIn(oldRecords)) {
                        record._.uses.add(recordList);
                        store._.ADD_QUEUE("onAdd", self.owner, self.name, record);
                    }
                })
            );
            const inverse = getInverse(recordList);
            for (const oldRecord of oldRecords) {
                if (oldRecord.notIn(newRecords)) {
                    oldRecord._.uses.delete(recordList);
                    store._.ADD_QUEUE("onDelete", self.owner, self.name, oldRecord);
                    if (inverse) {
                        oldRecord[inverse].delete(self.owner);
                    }
                }
            }
            recordList._proxy.data = newRecords.map((newRecord) => newRecord.localId);
            recordList._.syncLength(recordList);
        });
    }
    /**
     * Version of delete() that does not update the inverse.
     * This is internally called when inserting (with intent to delete)
     * on relational field with inverse, to prevent infinite loops.
     *
     * @param {RecordList} recordList
     * @param {...Record}
     */
    deleteNoinv(recordList, ...records) {
        const self = this;
        const store = recordList._store;
        for (const val of records) {
            const record = this.insert(
                recordList,
                val,
                function recordList_DeleteNoInv_Insert(record) {
                    const index = recordList.data.indexOf(record.localId);
                    if (index !== -1) {
                        const old = recordList._proxy.at(-1);
                        recordList.splice.call(recordList._proxy, index, 1);
                        self.syncLength(recordList);
                        old._.uses.delete(recordList);
                    }
                },
                { inv: false }
            );
            store._.ADD_QUEUE("onDelete", self.owner, self.name, record);
        }
    }
    /**
     * The internal reactive is only necessary to trigger outer reactives when
     * writing on it. As it has no callback, reading through it has no effect,
     * except slowing down performance and complexifying the stack.
     *
     * @param {RecordList} recordList
     * @param {RecordList} fullProxy
     */
    downgradeProxy(recordList, fullProxy) {
        return recordList._proxy === fullProxy ? recordList._proxyInternal : fullProxy;
    }
    /**
     * @param {RecordList} recordList
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
    insert(recordList, val, fn, { inv = true, mode = "ADD" } = {}) {
        const inverse = getInverse(recordList);
        const targetModel = getTargetModel(recordList);
        if (typeof val !== "object") {
            // single-id data
            val = { [recordList._store[targetModel].id]: val };
        }
        if (inverse && inv) {
            // special command to call addNoinv/deleteNoInv, to prevent infinite loop
            const target = isRecord(val) && val._raw === val ? val._proxy : val;
            target[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", recordList._.owner]];
        }
        /** @type {R} */
        let newRecordProxy;
        if (!isRecord(val)) {
            newRecordProxy = recordList._store[targetModel].preinsert(val);
        } else {
            newRecordProxy = val;
        }
        const newRecord = toRaw(newRecordProxy)._raw;
        fn?.(newRecord);
        if (!isRecord(val)) {
            // was preinserted, fully insert now
            recordList._store[targetModel].insert(val);
        }
        return newRecord;
    }
    /**
     * Sync reclist.data length with array length, as to not introduce confusion while debugging
     *
     * @param {RecordList} reclist
     */
    syncLength(reclist) {
        reclist.length = reclist.data.length;
    }
}

/** * @template {Record} R */
export class RecordList extends Array {
    /** @type {import("models").Store} */
    _store;
    /** @type {string[]} */
    data = [];
    /** @type {this} */
    _raw;
    /** @type {this} */
    _proxyInternal;
    /** @type {this} */
    _proxy;
    _ = markRaw(new RecordListInternal());

    constructor() {
        super();
        const recordList = this;
        recordList._raw = recordList;
        const recordListProxyInternal = new Proxy(recordList, {
            /** @param {RecordList<R>} receiver */
            get(recordList, name, recordListFullProxy) {
                recordListFullProxy = recordList._.downgradeProxy(recordList, recordListFullProxy);
                if (
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
                if (isComputeField(recordList) && !isEager(recordList)) {
                    setComputeInNeed(recordList);
                    if (isComputeOnNeed(recordList)) {
                        computeField(recordList);
                    }
                }
                if (name === "length") {
                    return recordListFullProxy.data.length;
                }
                if (isSortField(recordList) && !isEager(recordList)) {
                    setSortInNeed(recordList);
                    if (isSortOnNeed(recordList)) {
                        sortField(recordList);
                    }
                }
                if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                    // support for "array[index]" syntax
                    const index = parseInt(name);
                    return recordListFullProxy._store.recordByLocalId.get(
                        recordListFullProxy.data[index]
                    );
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
                                const oldRecord = toRaw(recordList._store.recordByLocalId).get(
                                    recordList.data[index]
                                );
                                if (oldRecord && oldRecord.notEq(newRecord)) {
                                    oldRecord._.uses.delete(recordList);
                                }
                                store._.ADD_QUEUE(
                                    "onDelete",
                                    recordList._.owner,
                                    recordList._.name,
                                    oldRecord
                                );
                                const inverse = getInverse(recordList);
                                if (inverse) {
                                    oldRecord[inverse].delete(recordList);
                                }
                                recordListProxy.data[index] = newRecord?.localId;
                                if (newRecord) {
                                    newRecord._.uses.add(recordList);
                                    store._.ADD_QUEUE(
                                        "onAdd",
                                        recordList._.owner,
                                        recordList._.name,
                                        newRecord
                                    );
                                    if (inverse) {
                                        newRecord[inverse].add(recordList);
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
        recordList._proxy = reactive(recordListProxyInternal);
        return recordList;
    }
    /** @param {R[]} records */
    push(...records) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListPush() {
            for (const val of records) {
                const record = recordList._.insert(
                    recordList,
                    val,
                    function recordListPushInsert(record) {
                        recordList._proxy.data.push(record.localId);
                        recordList._.syncLength(recordList);
                        record._.uses.add(recordList);
                    }
                );
                store._.ADD_QUEUE("onAdd", recordList._.owner, recordList._.name, record);
                const inverse = getInverse(recordList);
                if (inverse) {
                    record[inverse].add(recordList._.owner);
                }
            }
            return recordListFullProxy.data.length;
        });
    }
    /** @returns {R} */
    pop() {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
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
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListShift() {
            const recordProxy = recordListFullProxy._store.recordByLocalId.get(
                recordListFullProxy.data.shift()
            );
            recordList._.syncLength(recordList);
            if (!recordProxy) {
                return;
            }
            const record = toRaw(recordProxy)._raw;
            record._.uses.delete(recordList);
            store._.ADD_QUEUE("onDelete", recordList._.owner, recordList._.name, record);
            const inverse = getInverse(recordList);
            if (inverse) {
                record[inverse].delete(recordList._.owner);
            }
            return recordProxy;
        });
    }
    /** @param {R[]} records */
    unshift(...records) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListUnshift() {
            for (let i = records.length - 1; i >= 0; i--) {
                const record = recordList._.insert(recordList, records[i], (record) => {
                    recordList._proxy.data.unshift(record.localId);
                    recordList._.syncLength(recordList);
                    record._.uses.add(recordList);
                });
                store._.ADD_QUEUE("onAdd", recordList._.owner, recordList._.name, record);
                const inverse = getInverse(recordList);
                if (inverse) {
                    record[inverse].add(recordList._.owner);
                }
            }
            return recordListFullProxy.data.length;
        });
    }
    /** @param {R} recordProxy */
    indexOf(recordProxy) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
        return recordListFullProxy.data.indexOf(toRaw(recordProxy)?._raw.localId);
    }
    /**
     * @param {number} [start]
     * @param {number} [deleteCount]
     * @param {...R} [newRecordsProxy]
     */
    splice(start, deleteCount, ...newRecordsProxy) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
        const store = recordList._store;
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
            if (isOne(recordList) && start === 0 && deleteCount === 1) {
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
            for (const oldRecordProxy of oldRecordsProxy) {
                const oldRecord = toRaw(oldRecordProxy)._raw;
                oldRecord._.uses.delete(recordList);
                store._.ADD_QUEUE("onDelete", recordList._.owner, recordList._.name, oldRecord);
                const inverse = getInverse(recordList);
                if (inverse) {
                    oldRecord[inverse].delete(recordList._.owner);
                }
            }
            for (const newRecordProxy of newRecordsProxy) {
                const newRecord = toRaw(newRecordProxy)._raw;
                newRecord._.uses.add(recordList);
                store._.ADD_QUEUE("onAdd", recordList._.owner, recordList._.name, newRecord);
                const inverse = getInverse(recordList);
                if (inverse) {
                    newRecord[inverse].add(recordList._.owner);
                }
            }
        });
    }
    /** @param {(a: R, b: R) => boolean} func */
    sort(func) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListSort() {
            recordList._store._.sortRecordList(recordListFullProxy, func);
            return recordListFullProxy;
        });
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
        return recordListFullProxy.data
            .map((localId) => recordListFullProxy._store.recordByLocalId.get(localId))
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
            if (isOne(recordList)) {
                const last = records.at(-1);
                if (isRecord(last) && recordList.data.includes(toRaw(last)._raw.localId)) {
                    return last;
                }
                return recordList._.insert(
                    recordList,
                    last,
                    function recordListAddInsertOne(record) {
                        if (record.localId !== recordList.data[0]) {
                            recordList.splice.call(recordList._proxy, 0, 1, record);
                        }
                    }
                );
            }
            const res = [];
            for (const val of records) {
                if (isRecord(val) && recordList.data.includes(val.localId)) {
                    continue;
                }
                const rec = recordList._.insert(
                    recordList,
                    val,
                    function recordListAddInsertMany(record) {
                        if (recordList.data.indexOf(record.localId) === -1) {
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
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
        for (const localId of recordListFullProxy.data) {
            yield recordListFullProxy._store.recordByLocalId.get(localId);
        }
    }
    /** @param {number} index */
    at(index) {
        // this custom implement of "at" is slightly faster than auto-calling unimplement array method
        const recordList = toRaw(this)._raw;
        const recordListFullProxy = recordList._.downgradeProxy(recordList, this);
        return recordListFullProxy._store.recordByLocalId.get(recordListFullProxy.data.at(index));
    }
}
