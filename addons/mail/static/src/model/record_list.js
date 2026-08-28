import { isRecord, untrackFunctions } from "./misc";
import { RecordListInternal } from "./record_list_internal";

import { markRaw } from "@odoo/owl";

/** @typedef {import("./record").Record} Record */

/** * @template {Record} R */
export class RecordList extends Array {
    /** @returns {import("models").Store} */
    get _store() {
        return this._raw._.owner.store;
    }
    /** @type {this} */
    _raw;
    /** @type {this} */
    _proxy;
    _ = new RecordListInternal();

    constructor() {
        super();
        markRaw(this);
        const recordList = this;
        recordList._raw = recordList;
        recordList._.recordList = recordList;
        recordList._proxy = markRaw(
            new Proxy(recordList, {
                get: (target, name, receiver) => recordList._.proxyGet(name, receiver),
                set: (target, name, val, receiver) => recordList._.proxySet(name, val, receiver),
            })
        );
        return recordList;
    }
    /** @param {R[]} records */
    push(...records) {
        const recordList = this._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListPush() {
            const inverse = recordList._.getInverse();
            for (const val of records) {
                const record = recordList._.insert(val, function recordListPushInsert(record) {
                    recordList._.data().push(record);
                    recordList._.syncLength();
                    record._.uses.add(recordList);
                });
                store._.ADD_QUEUE("onAdd", recordList._.owner, recordList._.name, record);
                if (inverse) {
                    store._.updateFields(record, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
            return recordList._.data().length;
        });
    }
    /** @returns {R} */
    pop() {
        const recordList = this._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListPop() {
            /** @type {R} */
            const oldRecordProxy = recordList.at(-1);
            if (oldRecordProxy) {
                recordList.splice(recordList._.data().length - 1, 1);
            }
            return oldRecordProxy;
        });
    }
    /** @returns {R} */
    shift() {
        const recordList = this._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListShift() {
            const record = recordList._.data().shift();
            recordList._.syncLength();
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
        const recordList = this._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListUnshift() {
            const inverse = recordList._.getInverse();
            for (let i = records.length - 1; i >= 0; i--) {
                const record = recordList._.insert(records[i], (record) => {
                    recordList._.data().unshift(record);
                    recordList._.syncLength();
                    record._.uses.add(recordList);
                });
                store._.ADD_QUEUE("onAdd", recordList._.owner, recordList._.name, record);
                if (inverse) {
                    store._.updateFields(record, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
            return recordList._.data().length;
        });
    }
    /** @param {R} recordProxy */
    indexOf(recordProxy) {
        const recordList = this._raw;
        return recordList._.data().indexOf(recordProxy?._raw);
    }
    /**
     * @param {number} [start]
     * @param {number} [deleteCount]
     * @param {...R} [newRecordsProxy]
     */
    splice(start, deleteCount, ...newRecordsProxy) {
        const recordList = this._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListSplice() {
            const oldRecords = recordList._.data().slice(start, start + deleteCount);
            // splice on a copy, otherwise each in-place write would notify the list observers mid-splice
            const list = recordList._.data().slice();
            list.splice(
                start,
                deleteCount,
                ...newRecordsProxy.map((recordProxy) => recordProxy._raw)
            );
            recordList._.data.set(list);
            recordList._.syncLength();
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
        const recordList = this._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListSort() {
            store._.sortRecordList(recordList, func);
            return recordList._proxy;
        });
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        const recordList = this._raw;
        return recordList._.data()
            .map((record) => record._proxy)
            .concat(...collections.map((c) => [...c]));
    }
    /**
     * @param {...R}
     * @returns {R|R[]} the added record(s)
     */
    add(...records) {
        const recordList = this._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListAdd() {
            if (recordList._.isOne()) {
                const last = records.at(-1);
                if (isRecord(last) && recordList._.data().includes(last._raw)) {
                    return last;
                }
                return recordList._.insert(last, function recordListAddInsertOne(record) {
                    if (record !== recordList._.data()[0]) {
                        recordList.splice(0, 1, record._proxy);
                    }
                });
            }
            const res = [];
            for (const val of records) {
                if (isRecord(val) && recordList._.data().includes(val._raw)) {
                    continue;
                }
                const rec = recordList._.insert(val, function recordListAddInsertMany(record) {
                    if (recordList._.data().indexOf(record) === -1) {
                        recordList.push(record);
                    }
                });
                res.push(rec);
            }
            return res.length === 1 ? res[0] : res;
        });
    }
    /** @param {...R}  */
    delete(...records) {
        const recordList = this._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListDelete() {
            for (const val of records) {
                recordList._.insert(
                    val,
                    function recordListDelete_Insert(record) {
                        const index = recordList._.data().indexOf(record);
                        if (index !== -1) {
                            recordList.splice(index, 1);
                        }
                    },
                    { mode: "DELETE" }
                );
            }
        });
    }
    clear() {
        const recordList = this._raw;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListClear() {
            while (recordList._.data().length > 0) {
                recordList.pop();
            }
        });
    }
    /** @yields {R} */
    *[Symbol.iterator]() {
        const recordList = this._raw;
        for (const record of recordList._.data()) {
            yield record._proxy;
        }
    }
    /** @param {number} index */
    at(index) {
        // this custom implement of "at" is slightly faster than auto-calling unimplement array method
        const recordList = this._raw;
        return recordList._.data().at(index)?._proxy;
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
