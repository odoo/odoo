import { PgSnapshot } from "@mail/model/field_version";
import { Record } from "./record";
import { STORE_SYM, modelRegistry, untrackFunctions } from "./misc";

/** @typedef {import("./record_list").RecordList} RecordList */

export class Store extends Record {
    static singleton = true;
    /** @type {import("./store_internal").StoreInternal} */
    _;
    get [STORE_SYM]() {
        return true;
    }
    storeReady = false;

    handleError(err) {
        this._.ERRORS.push(err);
    }

    warnErrors = true;

    /**
     * Run `fn` as one update of the store, so that the rest of the app sees
     * everything `fn` writes as a single change.
     *
     * A write sets fields and relations one by one, so the data is only
     * consistent once the whole update is done. Until then:
     * - A computed field keeps its last value rather than computing one from
     *   half written data (`isUpdateInProgress`).
     * - The computes and the record deletions that the writes ask for wait
     *   in `FC_QUEUE` and `RD_QUEUE`, to run once at the end.
     * - An immediate onChange waits for the update and its queues to be done
     *   (`isDrainingQueues`), so it sees the final values.
     * - An error does not leave the store in the middle of an update: it goes
     *   to `ERRORS`, the update still ends, and then the first error is thrown.
     *
     * An update started inside another update joins the outer one (`UPDATE`,
     * `updateDepth`): only the outermost update runs the queues.
     *
     * @param {() => any} fn
     */
    MAKE_UPDATE(fn) {
        this._.raiseUpdateDepth();
        this._.UPDATE++;
        let res;
        try {
            res = fn();
        } catch (err) {
            this.handleError(err);
        }
        this._.UPDATE--;
        if (this._.UPDATE === 0) {
            this._.isDrainingQueues.set(true);
        }
        this._.lowerUpdateDepth();
        if (this._.UPDATE === 0) {
            // pretend an increased update cycle so that nothing in queue creates many small update cycles
            this._.UPDATE++;
            while (this._.FC_QUEUE.size > 0 || this._.RD_QUEUE.size > 0) {
                const FC_QUEUE = new Map(this._.FC_QUEUE);
                const RD_QUEUE = new Map(this._.RD_QUEUE);
                this._.FC_QUEUE.clear();
                this._.RD_QUEUE.clear();
                while (FC_QUEUE.size > 0) {
                    /** @type {[Record, Map<string, true>]} */
                    const [record, recMap] = FC_QUEUE.entries().next().value;
                    FC_QUEUE.delete(record);
                    for (const fieldName of recMap.keys()) {
                        record._.requestCompute(fieldName, { force: true });
                    }
                }
                while (RD_QUEUE.size > 0) {
                    /** @type {Record} */
                    const record = RD_QUEUE.keys().next().value;
                    RD_QUEUE.delete(record);
                    record._.isDeleted.set(true);
                    record._.scope?.destroy();
                    record.Model.records.delete(record.localId);
                    for (const [usingRecord, names] of record._.uses.data.entries()) {
                        for (const [name2, count] of names.entries()) {
                            for (let c = 0; c < count; c++) {
                                usingRecord[name2].delete(record);
                            }
                        }
                    }
                    for (const name of [
                        ...record.Model._.fieldsOne.keys(),
                        ...record.Model._.fieldsMany.keys(),
                    ]) {
                        const recordList = record[name];
                        for (const usedRecord of recordList._.data()) {
                            usedRecord._.uses.delete(recordList);
                        }
                        recordList._.data.set([]);
                        recordList._.syncLength();
                    }
                }
            }
            this._.UPDATE--;
            this._.isDrainingQueues.set(false);
            if (this._.ERRORS.length) {
                if (this.warnErrors) {
                    console.warn("Store data insert aborted due to following errors:");
                    for (const err of this._.ERRORS) {
                        console.warn(err);
                    }
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
            // Only consider the new "xip_list" format. Older payloads are applied
            // unversioned.
            this._.currentInsertVersion = versionMeta.snapshot.xip_list
                ? { ...versionMeta, snapshot: new PgSnapshot(versionMeta.snapshot) }
                : null;
        }
        try {
            Record.MAKE_UPDATE(function storeInsert() {
                const recordsDataToDelete = [];
                for (const [modelName, data] of Object.entries(dataByModelName)) {
                    if (!store[modelName]) {
                        console.warn(
                            `store.insert() received data for unknown model “${modelName}”.`
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
    _cleanupData(data) {
        super._cleanupData(data);
        if (this.Model.getName() === "Store") {
            delete data.Models;
            for (const [name] of modelRegistry.getEntries()) {
                delete data[name];
            }
        }
    }
}

untrackFunctions(Store.prototype, ["handleError", "insert"]);
