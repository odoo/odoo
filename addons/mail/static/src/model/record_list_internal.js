import { isRecord, untrackFunctions } from "./misc";

import { markRaw, signal } from "@odoo/owl";

/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

/** @param {RecordList} reclist */
export function getInverse(reclist) {
    return reclist._.owner.Model._.fieldsInverse.get(reclist._.name);
}

/** @param {RecordList} reclist */
export function getTargetModel(reclist) {
    return reclist._.owner.Model._.fieldsTargetModel.get(reclist._.name);
}

/** @param {RecordList} reclist */
export function isOne(reclist) {
    return reclist._.owner.Model._.fieldsOne.get(reclist._.name);
}

export class RecordListInternal {
    /** @type {import("@odoo/owl").Signal<Record[]>} raw */
    data = signal.Array();
    /** @type {string} */
    name;
    /** @type {Record} */
    owner;
    /** @type {RecordList} */
    recordList;
    /**
     * The store of the record this list belongs to, resolved on access: a list
     * made while the store is being made would freeze the bootstrap one.
     *
     * @returns {import("models").Store}
     */
    get store() {
        return this.owner.store;
    }
    /**
     * Bound methods returned by proxyGet, memoized so a method read does not
     * allocate a new bound function each time. Keyed by name; rebound when the
     * resolved function changes.
     *
     * @type {Map<string|symbol, { fn: Function, bound: Function }>}
     */
    boundFns = new Map();

    constructor() {
        markRaw(this);
    }

    /**
     * Technical construction of a record list: everything past the Array
     * bootstrap of the RecordList constructor, which delegates here. Sets up
     * the internal state and returns the record list: the proxy that
     * intercepts all content access.
     *
     * @param {RecordList} rawRecordList
     * @param {Record} [owner] the record whose relation field this list contains
     * @param {string} [name] the relation field name
     * @returns {RecordList}
     */
    setupRecordList(rawRecordList, owner, name) {
        const self = this;
        markRaw(rawRecordList); // record list is reactive through its data signal
        const recordList = new Proxy(rawRecordList, {
            get(...args) {
                return self.proxyGet(...args);
            },
            set(...args) {
                return self.proxySet(...args);
            },
        });
        markRaw(recordList); // record list is reactive through its data signal
        this.recordList = recordList;
        if (owner) {
            this.name = name;
            this.owner = owner;
        }
        return recordList;
    }
    /**
     * Version of add() that does not update the inverse.
     * This is internally called when inserting (with intent to add)
     * on relational field with inverse, to prevent infinite loops.
     *
     * @param {RecordList} recordList
     * @param {...Record}
     */
    addNoinv(...records) {
        const recordList = this.recordList;
        const self = this;
        if (isOne(recordList)) {
            const last = records.at(-1);
            if (isRecord(last) && last.in(recordList)) {
                return;
            }
            self.insert(
                last,
                function recordList_AddNoInvOneInsert(record) {
                    if (record !== self.data()[0]) {
                        const old = recordList.at(-1);
                        self.data().pop();
                        old?._.uses.delete(recordList);
                        self.data().push(record);
                        record._.uses.add(recordList);
                    }
                },
                { inv: false }
            );
            return;
        }
        for (const val of records) {
            if (isRecord(val) && val.in(recordList)) {
                continue;
            }
            self.insert(
                val,
                function recordList_AddNoInvManyInsert(record) {
                    if (self.data().indexOf(record) === -1) {
                        self.data().push(record);
                        record._.uses.add(recordList);
                    }
                },
                { inv: false }
            );
        }
    }
    /** @param {R[]|any[]} data */
    assign(data) {
        const recordList = this.recordList;
        const self = this;
        const store = this.store;
        return store.MAKE_UPDATE(function recordListAssign() {
            /** @type {Record[]|Set<Record>|RecordList<Record|any[]>} */
            const collection = isRecord(data) ? [data] : data;
            // data and collection could be same record list,
            // save before clear to not push mutated recordlist that is empty
            const vals = [...collection];
            const oldRecords = new Set(self.data());
            const newRecords = vals.map((val) =>
                self.insert(val, function recordListAssignInsert(record) {
                    if (!oldRecords.has(record)) {
                        record._.uses.add(recordList);
                    }
                })
            );
            const newRecordSet = new Set(newRecords);
            const inverse = getInverse(recordList);
            for (const oldRecord of oldRecords) {
                if (!newRecordSet.has(oldRecord)) {
                    oldRecord._.uses.delete(recordList);
                    if (inverse) {
                        store._.updateFields(oldRecord, {
                            [inverse]: [["DELETE", self.owner]],
                        });
                    }
                }
            }
            self.data.set(newRecords);
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
    deleteNoinv(...records) {
        const recordList = this.recordList;
        const self = this;
        for (const val of records) {
            self.insert(
                val,
                function recordList_DeleteNoInv_Insert(record) {
                    const index = self.data().indexOf(record);
                    if (index !== -1) {
                        recordList.splice(index, 1);
                    }
                },
                { inv: false }
            );
        }
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
    insert(val, fn, { inv = true, mode = "ADD" } = {}) {
        const recordList = this.recordList;
        const inverse = getInverse(recordList);
        const targetModel = getTargetModel(recordList);
        if (typeof val !== "object") {
            if (Array.isArray(this.store[targetModel].id)) {
                throw new Error(
                    `Cannot insert "${val}" on relational field "${this.owner.Model.getName()}/${
                        this.name
                    }": target model "${targetModel}" doesn't support single-id data!`
                );
            }
            // single-id data
            val = { [this.store[targetModel].id]: val };
        }
        if (inverse && inv) {
            // special command to call addNoinv/deleteNoInv, to prevent infinite loop
            const target = val;
            target[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", this.owner]];
        }
        /** @type {R} */
        let newRecord;
        if (!isRecord(val)) {
            newRecord = this.store[targetModel].preinsert(val);
        } else {
            newRecord = val;
        }
        fn?.(newRecord);
        if (!isRecord(val)) {
            // was preinserted, fully insert now
            this.store[targetModel].insert(val);
        }
        return newRecord;
    }
    proxyGet(rawRecordList, name, recordList) {
        if (name === "_") {
            return this;
        }
        if (name === "_store") {
            return this.store;
        }
        if (name === "length") {
            return this.data().length;
        }
        if (
            typeof name === "symbol" ||
            Object.hasOwn(rawRecordList, name) ||
            Object.hasOwn(rawRecordList.constructor.prototype, name)
        ) {
            const res = Reflect.get(...arguments);
            if (typeof res === "function") {
                const memo = this.boundFns.get(name);
                if (memo?.fn === res) {
                    return memo.bound;
                }
                const bound = res.bind(recordList);
                this.boundFns.set(name, { fn: res, bound });
                return bound;
            }
            return res;
        }
        const index = parseInt(name);
        if (!window.isNaN(index)) {
            return this.data()[index];
        }
        if (name === "reverse" || name === "fill" || name === "copyWithin") {
            throw new Error(
                `"${name}" is not supported on record lists: copy first (e.g. slice())`
            );
        }
        const array = [...rawRecordList[Symbol.iterator].call(recordList)];
        return array[name]?.bind(array);
    }
    proxySet(rawRecordList, name, val, recordList) {
        const self = this;
        const store = this.store;
        return store.MAKE_UPDATE(function recordListSet() {
            if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                // support for "array[index] = r3" syntax
                const index = parseInt(name);
                self.insert(val, function recordListSet_Insert(newRecord) {
                    const oldRecord = self.data()[index];
                    self.data()[index] = newRecord;
                    if (oldRecord && oldRecord.notEq(newRecord)) {
                        oldRecord._.uses.delete(recordList);
                    }
                    const inverse = getInverse(recordList);
                    if (inverse) {
                        store._.updateFields(oldRecord, {
                            [inverse]: [["DELETE", self.owner]],
                        });
                    }
                    if (newRecord) {
                        newRecord._.uses.add(recordList);
                        if (inverse) {
                            store._.updateFields(newRecord, {
                                [inverse]: [["ADD", self.owner]],
                            });
                        }
                    }
                });
            } else if (name === "length") {
                const newLength = parseInt(val);
                if (newLength !== self.data().length) {
                    if (newLength < self.data().length) {
                        recordList.splice(newLength, self.data().length - newLength);
                    }
                    self.data().length = newLength;
                }
            } else {
                return Reflect.set(rawRecordList, name, val, recordList);
            }
            return true;
        });
    }
    /**
     * Applies `func` as the order of the record list, in place.
     *
     * @param {RecordList} recordList
     * @param {(a: R, b: R) => number} func
     */
    sortRecordList(func) {
        const recordList = this.recordList;
        const records = [...this.data()];
        records.sort(func);
        const hasChanged = this.data().some((record, i) => record !== records[i]);
        if (hasChanged) {
            recordList.data = records;
        }
    }
}

untrackFunctions(RecordListInternal.prototype, ["assign", "proxySet"]);
