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
                    recordList.data.push(record);
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
            const record = recordList.data.shift();
            if (!record) {
                return;
            }
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
                    recordList.data.unshift(record);
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
     * Native read methods: they resolve records straight from `data`, so a
     * call does not copy the whole list first like the array-method fallback
     * of proxyGet does. Callbacks receive (record, index, this).
     */
    /** @param {(record: R, index: number, list: RecordList<R>) => any} fn */
    map(fn) {
        const recordList = this;
        return recordList.data.map((record, index) => fn(record, index, recordList));
    }
    /** @param {(record: R, index: number, list: RecordList<R>) => boolean} fn */
    filter(fn) {
        const recordList = this;
        const res = [];
        recordList.data.forEach((record, index) => {
            if (fn(record, index, recordList)) {
                res.push(record);
            }
        });
        return res;
    }
    /** @param {(record: R, index: number, list: RecordList<R>) => boolean} fn */
    find(fn) {
        const recordList = this;
        const index = recordList.findIndex(fn);
        return index === -1 ? undefined : recordList.at(index);
    }
    /** @param {(record: R, index: number, list: RecordList<R>) => boolean} fn */
    findIndex(fn) {
        const recordList = this;
        return recordList.data.findIndex((record, index) => fn(record, index, recordList));
    }
    /** @param {(record: R, index: number, list: RecordList<R>) => boolean} fn */
    some(fn) {
        return this.findIndex(fn) !== -1;
    }
    /** @param {(record: R, index: number, list: RecordList<R>) => boolean} fn */
    every(fn) {
        const recordList = this;
        return !recordList.some((record, index) => !fn(record, index, recordList));
    }
    /** @param {(record: R, index: number, list: RecordList<R>) => void} fn */
    forEach(fn) {
        const recordList = this;
        recordList.data.forEach((record, index) => fn(record, index, recordList));
    }
    /**
     * @param {(acc: any, record: R, index: number, list: RecordList<R>) => any} fn
     * @param {any} [init]
     */
    reduce(fn, ...init) {
        const recordList = this;
        const data = recordList.data;
        let index = 0;
        let acc;
        if (init.length) {
            acc = init[0];
        } else {
            if (data.length === 0) {
                throw new TypeError("Reduce of empty record list with no initial value");
            }
            acc = data[0];
            index = 1;
        }
        for (; index < data.length; index++) {
            acc = fn(acc, data[index], index, recordList);
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
            if (isOne(recordList) && start === 0 && deleteCount === 1) {
                // mutate the single slot: replacing the list fires every observer of it
                if (list.length === 0) {
                    recordList.data.pop();
                } else {
                    recordList.data[0] = list[0];
                }
            } else {
                recordList.data = list;
            }
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
