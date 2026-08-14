import { isRecord, untrackFunctions } from "./misc";

import { markRaw } from "@odoo/owl";

/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

export class RecordListInternal {
    /** @type {string} */
    name;
    /** @type {Record} */
    owner;
    /**
     * @type {boolean} Technical flag to immediately read attribute.
     * Useful to read `data` while passing to owl's proxy getter again to register observer.
     */
    gettingField = false;

    constructor() {
        markRaw(this);
    }

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
        if (this.isOne()) {
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
                .map((recordProxy) => recordProxy._raw);
            const newRecords = vals.map((val) =>
                self.insert(recordList, val, function recordListAssignInsert(record) {
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
            recordList._proxy.data = newRecords.map((newRecord) => newRecord.localId);
            recordList._.syncLength(recordList);
        });
    }
    computeField() {
        this.owner._.compute(this.owner, this.name, { fromInNeed: true });
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
                        recordList.splice.call(recordList._proxy, index, 1);
                        self.syncLength(recordList);
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
        const inverse = this.getInverse();
        const targetModel = this.getTargetModel();
        if (typeof val !== "object") {
            if (Array.isArray(recordList._store[targetModel].id)) {
                throw new Error(
                    `Cannot insert "${val}" on relational field "${recordList._.owner.Model.getName()}/${
                        recordList._.name
                    }": target model "${targetModel}" doesn't support single-id data!`
                );
            }
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
    setComputeInNeed() {
        this.owner._.fieldsComputeInNeed.set(this.name, true);
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

untrackFunctions(RecordListInternal.prototype, ["assign", "proxySet"]);
