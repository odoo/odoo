import { isRecord, untrackFunctions } from "./misc";
import { RecordListInternal } from "./record_list_internal";

import { markRaw } from "@odoo/owl";

/** @typedef {import("./record").Record} Record */

/** * @template {Record} R */
export class RecordList extends Array {
    /** @returns {import("models").Store} */
    get _store() {
        return this._.owner.store;
    }
    _ = new RecordListInternal();

    constructor() {
        super();
        markRaw(this);
        const recordList = markRaw(
            new Proxy(this, {
                get: (target, name) => target._.proxyGet(target, name),
                set: (target, name, val) => target._.proxySet(target, name, val),
            })
        );
        this._.recordList = recordList;
        return recordList;
    }
    /** @param {R[]} records */
    push(...records) {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListPush() {
            const inverse = recordList._.getInverse();
            for (const val of records) {
                const record = recordList._.insert(val, function recordListPushInsert(record) {
                    recordList._.data().push(record);
                    record._.uses.add(recordList);
                });
                if (inverse) {
                    store._.updateFields(record, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
            return recordList._.data().length;
        });
    }
    /** @returns {R} */
    pop() {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListPop() {
            /** @type {R} */
            const oldRecord = recordList.at(-1);
            if (oldRecord) {
                recordList.splice(recordList._.data().length - 1, 1);
            }
            return oldRecord;
        });
    }
    /** @returns {R} */
    shift() {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListShift() {
            const oldRecord = recordList.at(0);
            if (oldRecord) {
                recordList.splice(0, 1);
            }
            return oldRecord;
        });
    }
    /** @param {R[]} records */
    unshift(...records) {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListUnshift() {
            const inverse = recordList._.getInverse();
            for (let i = records.length - 1; i >= 0; i--) {
                const record = recordList._.insert(records[i], (record) => {
                    const list = recordList._.data().slice();
                    list.unshift(record);
                    recordList._.data.set(list);
                    record._.uses.add(recordList);
                });
                if (inverse) {
                    store._.updateFields(record, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
            return recordList._.data().length;
        });
    }
    /** @param {R} record */
    indexOf(record) {
        const recordList = this;
        return recordList._.data().indexOf(record);
    }
    /**
     * @param {number} [start]
     * @param {number} [deleteCount]
     * @param {...R} [newRecords]
     */
    splice(start, deleteCount, ...newRecords) {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListSplice() {
            const oldRecords = recordList._.data().slice(start, start + deleteCount);
            // splice on a copy, otherwise each in-place write would notify the list observers mid-splice
            const list = recordList._.data().slice();
            list.splice(start, deleteCount, ...newRecords);
            recordList._.data.set(list);
            const inverse = recordList._.getInverse();
            for (const oldRecord of oldRecords) {
                oldRecord._.uses.delete(recordList);
                if (inverse) {
                    store._.updateFields(oldRecord, {
                        [inverse]: [["DELETE", recordList._.owner]],
                    });
                }
            }
            for (const newRecord of newRecords) {
                newRecord._.uses.add(recordList);
                if (inverse) {
                    store._.updateFields(newRecord, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
        });
    }
    /** @param {(a: R, b: R) => boolean} func */
    sort(func) {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListSort() {
            store._.sortRecordList(recordList, func);
            return recordList;
        });
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        const recordList = this;
        return recordList._.data().concat(...collections.map((c) => [...c]));
    }
    /**
     * @param {...R}
     * @returns {R|R[]} the added record(s)
     */
    add(...records) {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListAdd() {
            if (recordList._.isOne()) {
                const last = records.at(-1);
                if (isRecord(last) && recordList._.data().includes(last)) {
                    return last;
                }
                return recordList._.insert(last, function recordListAddInsertOne(record) {
                    if (record !== recordList._.data()[0]) {
                        recordList.splice(0, 1, record);
                    }
                });
            }
            const res = [];
            for (const val of records) {
                if (isRecord(val) && recordList._.data().includes(val)) {
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
        const recordList = this;
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
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListClear() {
            while (recordList._.data().length > 0) {
                recordList.pop();
            }
        });
    }
    /** @yields {R} */
    *[Symbol.iterator]() {
        const recordList = this;
        yield* recordList._.data();
    }
    /** @param {number} index */
    at(index) {
        // this custom implement of "at" is slightly faster than auto-calling unimplement array method
        const recordList = this;
        return recordList._.data().at(index);
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => any} fn
     * @param {any} [thisArg]
     */
    map(fn, thisArg) {
        const recordList = this;
        return recordList._.data().map((record, index) =>
            fn.call(thisArg, record, index, recordList)
        );
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => boolean} fn
     * @param {any} [thisArg]
     */
    filter(fn, thisArg) {
        const recordList = this;
        const res = [];
        recordList._.data().forEach((record, index) => {
            if (fn.call(thisArg, record, index, recordList)) {
                res.push(record);
            }
        });
        return res;
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => void} fn
     * @param {any} [thisArg]
     */
    forEach(fn, thisArg) {
        const recordList = this;
        recordList._.data().forEach((record, index) => fn.call(thisArg, record, index, recordList));
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => boolean} fn
     * @param {any} [thisArg]
     */
    findIndex(fn, thisArg) {
        const recordList = this;
        return recordList._.data().findIndex((record, index) =>
            fn.call(thisArg, record, index, recordList)
        );
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => boolean} fn
     * @param {any} [thisArg]
     */
    find(fn, thisArg) {
        const recordList = this;
        return recordList._.data().find((record, index) =>
            fn.call(thisArg, record, index, recordList)
        );
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => boolean} fn
     * @param {any} [thisArg]
     */
    some(fn, thisArg) {
        return this.findIndex(fn, thisArg) !== -1;
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => boolean} fn
     * @param {any} [thisArg]
     */
    every(fn, thisArg) {
        const recordList = this;
        return !recordList.some((record, index) => !fn.call(thisArg, record, index, recordList));
    }
    /**
     * @param {(acc: any, record: R, index: number, list: RecordList<R>) => any} fn
     * @param {any} [init]
     */
    reduce(fn, ...init) {
        const recordList = this;
        const records = recordList._.data();
        const { length } = records;
        let index = 0;
        let acc;
        if (init.length) {
            acc = init[0];
        } else {
            if (length === 0) {
                throw new TypeError("Reduce of empty record list with no initial value");
            }
            acc = records[0];
            index = 1;
        }
        for (; index < length; index++) {
            acc = fn(acc, records[index], index, recordList);
        }
        return acc;
    }
    /**
     * @param {number} [start]
     * @param {number} [end]
     */
    slice(start, end) {
        const recordList = this;
        return recordList._.data().slice(start, end);
    }
    /** @param {R} record */
    includes(record) {
        return this.indexOf(record) !== -1;
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
