import { isRecord, untrackFunctions } from "./misc";

import { markRaw, signal } from "@odoo/owl";

/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

export class RecordListInternal {
    /** @type {import("@odoo/owl").Signal<Record[]>} raw */
    data = signal.Array();
    /** @type {string} */
    name;
    /** @type {Record} */
    owner;
    /** @type {RecordList} */
    recordList;

    constructor() {
        markRaw(this);
    }

    /**
     * Version of add() that does not update the inverse.
     * This is internally called when inserting (with intent to add)
     * on relational field with inverse, to prevent infinite loops.
     *
     * @param {...Record}
     */
    addNoinv(...records) {
        const self = this;
        const recordList = this.recordList;
        const store = recordList._store;
        if (this.isOne()) {
            const last = records.at(-1);
            if (isRecord(last) && last.in(recordList)) {
                return;
            }
            const record = self.insert(
                last,
                function recordList_AddNoInvOneInsert(record) {
                    if (record !== self.data()[0]) {
                        const old = recordList.at(-1);
                        self.data().pop();
                        old?._.uses.delete(recordList);
                        self.data().push(record);
                        self.syncLength();
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
                val,
                function recordList_AddNoInvManyInsert(record) {
                    if (self.data().indexOf(record) === -1) {
                        self.data().push(record);
                        self.syncLength();
                        record._.uses.add(recordList);
                    }
                },
                { inv: false }
            );
            store._.ADD_QUEUE("onAdd", self.owner, self.name, record);
        }
    }
    /** @param {R[]|any[]} data */
    assign(data) {
        const self = this;
        const recordList = this.recordList;
        const store = recordList._store;
        return store.MAKE_UPDATE(function recordListAssign() {
            /** @type {Record[]|Set<Record>|RecordList<Record|any[]>} */
            const collection = isRecord(data) ? [data] : data;
            // data and collection could be same record list,
            // save before clear to not push mutated recordlist that is empty
            const vals = [...collection];
            const oldRecords = [...recordList].map((recordProxy) => recordProxy._raw);
            const newRecords = vals.map((val) =>
                self.insert(val, function recordListAssignInsert(record) {
                    if (record.notIn(oldRecords)) {
                        record._.uses.add(recordList);
                        store._.ADD_QUEUE("onAdd", self.owner, self.name, record);
                    }
                })
            );
            const inverse = self.getInverse();
            for (const oldRecord of oldRecords) {
                if (oldRecord.notIn(newRecords)) {
                    oldRecord._.uses.delete(recordList);
                    store._.ADD_QUEUE("onDelete", self.owner, self.name, oldRecord);
                    if (inverse) {
                        store._.updateFields(oldRecord, {
                            [inverse]: [["DELETE", self.owner]],
                        });
                    }
                }
            }
            self.data.set(newRecords);
            self.syncLength();
        });
    }
    computeField() {
        this.owner._.compute(this.name, { fromInNeed: true });
    }
    /**
     * Version of delete() that does not update the inverse.
     * This is internally called when inserting (with intent to delete)
     * on relational field with inverse, to prevent infinite loops.
     *
     * @param {...Record}
     */
    deleteNoinv(...records) {
        const self = this;
        const recordList = this.recordList;
        const store = recordList._store;
        for (const val of records) {
            const record = this.insert(
                val,
                function recordList_DeleteNoInv_Insert(record) {
                    const index = self.data().indexOf(record);
                    if (index !== -1) {
                        recordList.splice(index, 1);
                        self.syncLength();
                    }
                },
                { inv: false }
            );
            store._.ADD_QUEUE("onDelete", self.owner, self.name, record);
        }
    }
    getInverse() {
        return this.owner.Model._.fieldsInverse.get(this.name);
    }
    getTargetModel() {
        return this.owner.Model._.fieldsTargetModel.get(this.name);
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
    insert(val, fn, { inv = true, mode = "ADD" } = {}) {
        const recordList = this.recordList;
        const inverse = this.getInverse();
        const targetModel = this.getTargetModel();
        if (typeof val !== "object") {
            if (Array.isArray(recordList._store[targetModel].id)) {
                throw new Error(
                    `Cannot insert "${val}" on relational field "${this.owner.Model.getName()}/${
                        this.name
                    }": target model "${targetModel}" doesn't support single-id data!`
                );
            }
            // single-id data
            val = { [recordList._store[targetModel].id]: val };
        }
        if (inverse && inv) {
            // special command to call addNoinv/deleteNoInv, to prevent infinite loop
            const target = isRecord(val) && val._raw === val ? val._proxy : val;
            target[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", this.owner]];
        }
        /** @type {R} */
        let newRecordProxy;
        if (!isRecord(val)) {
            newRecordProxy = recordList._store[targetModel].preinsert(val);
        } else {
            newRecordProxy = val;
        }
        const newRecord = newRecordProxy._raw;
        fn?.(newRecord);
        if (!isRecord(val)) {
            // was preinserted, fully insert now
            recordList._store[targetModel].insert(val);
        }
        return newRecord;
    }
    isComputeField() {
        return this.owner.Model._.fieldsCompute.get(this.name);
    }
    isComputeOnNeed() {
        return this.owner._.fieldsComputeOnNeed.get(this.name);
    }
    isEager() {
        return this.owner.Model._.fieldsEager.get(this.name);
    }
    isOne() {
        return this.owner.Model._.fieldsOne.get(this.name);
    }
    /**
     * @param {string} name
     * @param {RecordList} recordListProxy
     */
    proxyGet(name, recordListProxy) {
        const recordList = this.recordList;
        if (
            typeof name === "symbol" ||
            (name !== "length" && Object.hasOwn(recordList, name)) ||
            Object.prototype.hasOwnProperty.call(recordList.constructor.prototype, name)
        ) {
            let res = Reflect.get(recordList, name, recordListProxy);
            if (typeof res === "function") {
                res = res.bind(recordListProxy);
            }
            return res;
        }
        if (this.isComputeField() && !this.isEager()) {
            this.setComputeInNeed();
            if (this.isComputeOnNeed()) {
                this.computeField();
            }
        }
        if (name === "length") {
            return this.data().length;
        }
        const index = parseInt(name);
        if (!window.isNaN(index)) {
            // support for "array[index]" syntax
            return this.data()[index]?._proxy;
        }
        // Attempt an unimplemented array method call
        const array = [...recordList];
        return array[name]?.bind(array);
    }
    /**
     * @param {string} name
     * @param {any} val
     * @param {RecordList} recordListProxy
     */
    proxySet(name, val, recordListProxy) {
        const self = this;
        const recordList = this.recordList;
        const store = recordList._store;
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
                    store._.ADD_QUEUE("onDelete", self.owner, self.name, oldRecord);
                    const inverse = self.getInverse();
                    if (inverse) {
                        store._.updateFields(oldRecord, {
                            [inverse]: [["DELETE", self.owner]],
                        });
                    }
                    if (newRecord) {
                        newRecord._.uses.add(recordList);
                        store._.ADD_QUEUE("onAdd", self.owner, self.name, newRecord);
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
                        recordList.splice(newLength, recordList.length - newLength);
                    }
                    self.data().length = newLength;
                    self.syncLength();
                }
            } else {
                return Reflect.set(recordList, name, val, recordListProxy);
            }
            return true;
        });
    }
    setComputeInNeed() {
        this.owner._.fieldsComputeInNeed.set(this.name, true);
    }
    /**
     * Sync the data length with the array length, as to not introduce confusion while debugging
     */
    syncLength() {
        this.recordList.length = this.data().length;
    }
}

untrackFunctions(RecordListInternal.prototype, ["assign", "proxySet"]);
