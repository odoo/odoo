import { PgSnapshot } from "@mail/model/field_version";
import { Record } from "./record";
import { STORE_SYM, modelRegistry, untrackFunctions } from "./misc";

import { immediateEffect, toRaw, untrack } from "@odoo/owl";

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

    /** @param {() => any} fn */
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
        this._.lowerUpdateDepth();
        if (this._.UPDATE === 0) {
            // pretend an increased update cycle so that nothing in queue creates many small update cycles
            this._.UPDATE++;
            while (
                this._.FC_QUEUE.size > 0 ||
                this._.FA_QUEUE.size > 0 ||
                this._.FD_QUEUE.size > 0 ||
                this._.FU_QUEUE.size > 0 ||
                this._.RD_QUEUE.size > 0
            ) {
                const FC_QUEUE = new Map(this._.FC_QUEUE);
                const FA_QUEUE = new Map(this._.FA_QUEUE);
                const FD_QUEUE = new Map(this._.FD_QUEUE);
                const FU_QUEUE = new Map(this._.FU_QUEUE);
                const RD_QUEUE = new Map(this._.RD_QUEUE);
                this._.FC_QUEUE.clear();
                this._.FA_QUEUE.clear();
                this._.FD_QUEUE.clear();
                this._.FU_QUEUE.clear();
                this._.RD_QUEUE.clear();
                while (FC_QUEUE.size > 0) {
                    /** @type {[Record, Map<string, true>]} */
                    const [record, recMap] = FC_QUEUE.entries().next().value;
                    FC_QUEUE.delete(record);
                    for (const fieldName of recMap.keys()) {
                        record._.requestCompute(fieldName, { force: true });
                    }
                }
                while (FA_QUEUE.size > 0) {
                    /** @type {[Record, Map<string, Map<Record, true>>]} */
                    const [record, recMap] = FA_QUEUE.entries().next().value;
                    FA_QUEUE.delete(record);
                    while (recMap.size > 0) {
                        /** @type {[string, Map<Record, true>]} */
                        const [fieldName, fieldMap] = recMap.entries().next().value;
                        recMap.delete(fieldName);
                        const onAdd = record.Model._.fieldsOnAdd.get(fieldName);
                        for (const addedRec of fieldMap.keys()) {
                            try {
                                onAdd?.call(record._proxy, addedRec._proxy);
                            } catch (err) {
                                this.handleError(err);
                            }
                        }
                    }
                }
                while (FD_QUEUE.size > 0) {
                    /** @type {[Record, Map<string, Map<Record, true>>]} */
                    const [record, recMap] = FD_QUEUE.entries().next().value;
                    FD_QUEUE.delete(record);
                    while (recMap.size > 0) {
                        /** @type {[string, Map<Record, true>]} */
                        const [fieldName, fieldMap] = recMap.entries().next().value;
                        recMap.delete(fieldName);
                        const onDelete = record.Model._.fieldsOnDelete.get(fieldName);
                        for (const removedRec of fieldMap.keys()) {
                            try {
                                onDelete?.call(
                                    record._proxy,
                                    removedRec.exists() ? removedRec._proxy : undefined
                                );
                            } catch (err) {
                                this.handleError(err);
                            }
                        }
                    }
                }
                while (FU_QUEUE.size > 0) {
                    /** @type {[Record, Map<string, true>]} */
                    const [record, map] = FU_QUEUE.entries().next().value;
                    FU_QUEUE.delete(record);
                    for (const fieldName of map.keys()) {
                        record._.onUpdate(fieldName);
                    }
                }
                while (RD_QUEUE.size > 0) {
                    /** @type {Record} */
                    const record = RD_QUEUE.keys().next().value;
                    RD_QUEUE.delete(record);
                    record._.isDeleted.set(true);
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
                        recordList._.data().length = 0;
                    }
                    record._runDisposeFns();
                }
            }
            this._.UPDATE--;
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
            this._.currentInsertVersion = {
                ...versionMeta,
                snapshot: new PgSnapshot(versionMeta.snapshot),
            };
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
    /**
     * Version of onChange where the callback receives observe function as param.
     * This is useful when there's desire to postpone calling the callback function,
     * in which the observe is also intended to have its invocation postponed.
     *
     * @param {Record} recordProxy
     * @param {string|string[]} key
     * @param {(observe: Function) => any} callback
     * @returns {function} function to call to stop observing changes
     */
    _onChange(recordProxy, key, callback) {
        function _observe() {
            // access recordProxy[key] only once to avoid triggering reactive get() many times
            const val = recordProxy[key];
            if (typeof val === "object" && val !== null) {
                void Object.keys(val);
            }
            if (Array.isArray(val)) {
                void val.length;
                void toRaw(val).forEach.call(val, (i) => i);
            }
        }
        if (Array.isArray(key)) {
            /** @type {Function[]} */
            const arrayDisposeFns = [];
            for (const k of key) {
                arrayDisposeFns.push(this._onChange(recordProxy, k, callback));
            }
            return () => {
                arrayDisposeFns.forEach((f) => f());
                arrayDisposeFns.length = 0;
            };
        }
        let running = false;
        const disposeFn = untrack(() =>
            immediateEffect(() => {
                if (!running) {
                    _observe();
                } else {
                    callback(_observe);
                }
            })
        );
        running = true;
        return disposeFn;
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
