import { isRecord, untrackFunctions } from "./misc";
import { RecordListInternal, getInverse, isOne } from "./record_list_internal";

/** @typedef {import("./record").Record} Record */

/** * @template {Record} R */
export class RecordList extends Array {
    _ = new RecordListInternal();
    /** @type {Record[]} */
    get data() {
        return this._.data();
    }
    set data(records) {
        this._.data.set(records);
    }

    /**
     * @param {number} length forwarded to Array: array methods (map, slice,
     *   ...) construct their result through this class and pass the length
     *   alone (such a result contains no relation, it is just data)
     * @param {Record} [owner] the record whose relation field this list contains
     * @param {string} [name] the relation field name
     */
    constructor(length, owner, name) {
        super(length);
        return this._.setupRecordList(this, owner, name);
    }
    /** @param {R[]} records */
    push(...records) {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListPush() {
            const inverse = getInverse(recordList);
            for (const val of records) {
                const record = recordList._.insert(val, function recordListPushInsert(record) {
                    recordList.data = [...recordList.data, record];
                    record._.uses.add(recordList);
                });
                if (inverse) {
                    store._.updateFields(record, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
            return recordList.data.length;
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
                recordList.splice(recordList.length - 1, 1);
            }
            return oldRecord;
        });
    }
    /** @returns {R} */
    shift() {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListShift() {
            const [record, ...rest] = recordList.data;
            if (!record) {
                return;
            }
            recordList.data = rest;
            record._.uses.delete(recordList);
            const inverse = getInverse(recordList);
            if (inverse) {
                store._.updateFields(record, { [inverse]: [["DELETE", recordList._.owner]] });
            }
            return record;
        });
    }
    /** @param {R[]} records */
    unshift(...records) {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListUnshift() {
            const inverse = getInverse(recordList);
            for (let i = records.length - 1; i >= 0; i--) {
                const record = recordList._.insert(records[i], (record) => {
                    recordList.data = [record, ...recordList.data];
                    record._.uses.add(recordList);
                });
                if (inverse) {
                    store._.updateFields(record, { [inverse]: [["ADD", recordList._.owner]] });
                }
            }
            return recordList.data.length;
        });
    }
    /**
     * Read methods of Array, implemented on the records themselves: the
     * fallback of proxyGet spreads the whole list into an array before it can
     * call the Array one. Each walks the records the call started on, so a
     * write from the callback lands on the next read, not on this one.
     *
     * @param {(record: R, index: number, list: RecordList<R>) => any} fn
     * @param {any} [thisArg]
     */
    map(fn, thisArg) {
        const recordList = this;
        return recordList.data.map((record, index) => fn.call(thisArg, record, index, recordList));
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => boolean} fn
     * @param {any} [thisArg]
     */
    filter(fn, thisArg) {
        const recordList = this;
        const res = [];
        for (const [index, record] of recordList.data.entries()) {
            if (fn.call(thisArg, record, index, recordList)) {
                res.push(record);
            }
        }
        return res;
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => boolean} fn
     * @param {any} [thisArg]
     */
    find(fn, thisArg) {
        const recordList = this;
        const records = recordList.data;
        const index = records.findIndex((record, i) => fn.call(thisArg, record, i, recordList));
        return index === -1 ? undefined : records[index];
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => boolean} fn
     * @param {any} [thisArg]
     */
    findIndex(fn, thisArg) {
        const recordList = this;
        return recordList.data.findIndex((record, index) =>
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
        return (
            recordList.findIndex(
                (record, index) => !fn.call(thisArg, record, index, recordList)
            ) === -1
        );
    }
    /**
     * @param {(record: R, index: number, list: RecordList<R>) => void} fn
     * @param {any} [thisArg]
     */
    forEach(fn, thisArg) {
        const recordList = this;
        for (const [index, record] of recordList.data.entries()) {
            fn.call(thisArg, record, index, recordList);
        }
    }
    /**
     * @param {(acc: any, record: R, index: number, list: RecordList<R>) => any} fn
     * @param {any} [init]
     */
    reduce(fn, ...init) {
        const recordList = this;
        const records = recordList.data;
        let index = 0;
        let acc;
        if (init.length) {
            acc = init[0];
        } else {
            if (records.length === 0) {
                throw new TypeError("Reduce of empty record list with no initial value");
            }
            acc = records[0];
            index = 1;
        }
        for (; index < records.length; index++) {
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
        return recordList.data.slice(start, end);
    }
    /** @param {R} record */
    includes(record) {
        return this.data.includes(record);
    }
    /** @param {R} record */
    indexOf(record) {
        const recordList = this;
        return recordList.data.indexOf(record);
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
            const oldRecords = recordList.data.slice(start, start + deleteCount);
            const list = recordList.data.slice(); // splice on copy of list so that reactive observers not triggered while splicing
            list.splice(start, deleteCount, ...newRecords);
            recordList.data = list;
            const inverse = getInverse(recordList);
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
            recordList._.sortRecordList(func);
            return recordList;
        });
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        const recordList = this;
        return recordList.data.concat(...collections.map((c) => [...c]));
    }
    /**
     * @param {...R}
     * @returns {R|R[]} the added record(s)
     */
    add(...records) {
        const recordList = this;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListAdd() {
            if (isOne(recordList)) {
                const last = records.at(-1);
                if (isRecord(last) && recordList.data.includes(last)) {
                    return last;
                }
                return recordList._.insert(last, function recordListAddInsertOne(record) {
                    if (record !== recordList.data[0]) {
                        recordList.splice(0, 1, record);
                    }
                });
            }
            const res = [];
            for (const val of records) {
                if (isRecord(val) && recordList.data.includes(val)) {
                    continue;
                }
                const rec = recordList._.insert(val, function recordListAddInsertMany(record) {
                    if (recordList.data.indexOf(record) === -1) {
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
                        const index = recordList.data.indexOf(record);
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
            while (recordList.data.length > 0) {
                recordList.pop();
            }
        });
    }
    /** @yields {R} */
    *[Symbol.iterator]() {
        const recordList = this;
        yield* recordList.data;
    }
    /** @param {number} index */
    at(index) {
        // this custom implement of "at" is slightly faster than auto-calling unimplement array method
        const recordList = this;
        return recordList.data.at(index);
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
