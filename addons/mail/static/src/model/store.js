import { PgSnapshot } from "@mail/model/field_version";
import { Record } from "./record";
import { STORE_SYM, untrackFunctions } from "./misc";

/** @typedef {import("./record_list").RecordList} RecordList */

export class Store extends Record {
    static singleton = true;
    /** @type {import("./store_internal").StoreInternal} */
    _;
    get [STORE_SYM]() {
        return true;
    }
    /**
     * All the records of the store, by localId (raw own property of the store
     * record, set by RecordInternal.setupRecord).
     *
     * @type {Map<string, Record>}
     */
    recordByLocalId;
    /**
     * @param {string} localId
     * @returns {Record}
     */
    get(localId) {
        return this.recordByLocalId.get(localId);
    }

    handleError(err) {
        this._.ERRORS.push(err);
    }

    warnErrors = true;

    /** @param {() => any} fn */
    MAKE_UPDATE(fn) {
        this._.UPDATE++;
        let res;
        try {
            res = fn();
        } catch (err) {
            this.handleError(err);
        }
        this._.UPDATE--;
        if (this._.UPDATE === 0) {
            // pretend an increased update cycle so that nothing in queue creates many small update cycles
            this._.UPDATE++;
            while (this._.RD_QUEUE.size > 0) {
                const RD_QUEUE = new Map(this._.RD_QUEUE);
                this._.RD_QUEUE.clear();
                this._.deletingRecords.set(true);
                while (RD_QUEUE.size > 0) {
                    /** @type {Record} */
                    const record = RD_QUEUE.keys().next().value;
                    RD_QUEUE.delete(record);
                    record._runDisposeFns();
                    record._.deletingSignal.set(true);
                    for (const [usingRecord, names] of record._.uses.data.entries()) {
                        for (const [name2, count] of names.entries()) {
                            const usingList = usingRecord._.fieldsList.get(name2);
                            for (let c = 0; c < count; c++) {
                                usingList.delete(record);
                            }
                        }
                    }
                    for (const name of [
                        ...record.Model._.fieldsOne.keys(),
                        ...record.Model._.fieldsMany.keys(),
                    ]) {
                        const recordList = record._.fieldsList.get(name);
                        if (!recordList) {
                            continue;
                        }
                        for (const usedRecord of recordList) {
                            usedRecord._.uses.delete(recordList);
                        }
                        recordList.clear();
                    }
                    this.recordByLocalId.delete(record.localId);
                    record.Model.records.delete(record.localId);
                    record._.existsSignal.set(false);
                }
                this._.deletingRecords.set(false);
            }
            this._.UPDATE--;
            if (this._.ERRORS.length) {
                if (this._.warnErrors) {
                    console.warn(
                        "Store data insert aborted due to following errors: " +
                            this._.ERRORS.map((e) => e?.message ?? String(e)).join(" | ")
                    );
                }
                const [error1] = this._.ERRORS;
                this._.ERRORS = [];
                throw error1;
            }
        }
        return res;
    }
    /**
     * @template T
     * @param {T & {__store_version__?: import("@mail/model/field_version").StoreVersion}} [dataByModelName={}]
     * @param {Object} [options={}]
     * @returns {{ [K in keyof T]: import("models").Models[K][] }}
     */
    insert(dataByModelName = {}, options = {}) {
        const store = this;
        // Only cleanup if we initiated the insert.
        const shouldCleanup = !this._.currentInsertVersion;
        if ("__store_version__" in dataByModelName) {
            const versionMeta = dataByModelName.__store_version__;
            delete dataByModelName.__store_version__;
            this._.currentInsertVersion = {
                ...versionMeta,
                snapshot: new PgSnapshot(versionMeta.snapshot),
            };
        }
        try {
            this.MAKE_UPDATE(function storeInsert() {
                const recordsDataToDelete = [];
                for (const [modelName, data] of Object.entries(dataByModelName)) {
                    if (!store[modelName]) {
                        console.warn(
                            `store.insert() received data for unknown model "${modelName}".`
                        );
                        continue;
                    }
                    const insertData = [];
                    for (const vals of Array.isArray(data) ? data : [data]) {
                        if (vals._DELETE) {
                            delete vals._DELETE;
                            recordsDataToDelete.push([modelName, vals]);
                        } else {
                            insertData.push(vals);
                        }
                    }
                    store[modelName].insert(insertData, options);
                }
                // Delete after all inserts to make sure a relation potentially registered before the
                // delete doesn't re-add the deleted record by mistake.
                for (const [modelName, vals] of recordsDataToDelete) {
                    store[modelName].get(vals)?.delete();
                }
            });
        } finally {
            if (shouldCleanup) {
                this._.currentInsertVersion = null;
            }
        }
    }
}
untrackFunctions(Store.prototype, ["handleError", "insert", "onChange"]);
