import { Record } from "./record";
import { STORE_SYM, modelRegistry } from "./misc";
import { reactive, toRaw } from "@odoo/owl";

/** @typedef {import("./record_list").RecordList} RecordList */

export const storeInsertFns = {
    makeContext(store) {},
    getActualModelName(store, ctx, pyOrJsModelName) {
        return pyOrJsModelName;
    },
    getExtraFieldsFromModel(store) {},
};

export class Store extends Record {
    /** @type {import("./store_internal").StoreInternal} */
    _;
    [STORE_SYM] = true;
    /** @type {Map<string, Record>} */
    recordByLocalId;
    storeReady = false;
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
        const deletingRecordsByLocalId = new Map();
        if (this._.UPDATE === 0) {
            // pretend an increased update cycle so that nothing in queue creates many small update cycles
            this._.UPDATE++;
            while (
                this._.FC_QUEUE.size > 0 ||
                this._.FS_QUEUE.size > 0 ||
                this._.FA_QUEUE.size > 0 ||
                this._.FD_QUEUE.size > 0 ||
                this._.FU_QUEUE.size > 0 ||
                this._.RO_QUEUE.size > 0 ||
                this._.RD_QUEUE.size > 0 ||
                this._.RHD_QUEUE.size > 0
            ) {
                const FC_QUEUE = new Map(this._.FC_QUEUE);
                const FS_QUEUE = new Map(this._.FS_QUEUE);
                const FA_QUEUE = new Map(this._.FA_QUEUE);
                const FD_QUEUE = new Map(this._.FD_QUEUE);
                const FU_QUEUE = new Map(this._.FU_QUEUE);
                const RO_QUEUE = new Map(this._.RO_QUEUE);
                const RD_QUEUE = new Map(this._.RD_QUEUE);
                const RHD_QUEUE = new Map(this._.RHD_QUEUE);
                this._.FC_QUEUE.clear();
                this._.FS_QUEUE.clear();
                this._.FA_QUEUE.clear();
                this._.FD_QUEUE.clear();
                this._.FU_QUEUE.clear();
                this._.RO_QUEUE.clear();
                this._.RD_QUEUE.clear();
                this._.RHD_QUEUE.clear();
                while (FC_QUEUE.size > 0) {
                    /** @type {[Record, Map<string, true>]} */
                    const [record, recMap] = FC_QUEUE.entries().next().value;
                    FC_QUEUE.delete(record);
                    for (const fieldName of recMap.keys()) {
                        record._.requestCompute(record, fieldName, { force: true });
                    }
                }
                while (FS_QUEUE.size > 0) {
                    /** @type {[Record, Map<string, true>]} */
                    const [record, recMap] = FS_QUEUE.entries().next().value;
                    FS_QUEUE.delete(record);
                    for (const fieldName of recMap.keys()) {
                        record._.requestSort(record, fieldName, { force: true });
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
                                onDelete?.call(record._proxy, removedRec._proxy);
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
                        record._.onUpdate(record, fieldName);
                    }
                }
                while (RO_QUEUE.size > 0) {
                    /** @type {Map<Function, true>} */
                    const cb = RO_QUEUE.keys().next().value;
                    RO_QUEUE.delete(cb);
                    try {
                        cb();
                    } catch (err) {
                        this.handleError(err);
                    }
                }
                while (RD_QUEUE.size > 0) {
                    /** @type {Record} */
                    const record = RD_QUEUE.keys().next().value;
                    RD_QUEUE.delete(record);
                    for (const [localId, names] of record._.uses.data.entries()) {
                        for (const [name2, count] of names.entries()) {
                            const existingRecordProxyInternal = toRaw(this.recordByLocalId).get(
                                localId
                            );
                            const usingRecord =
                                (existingRecordProxyInternal &&
                                    toRaw(existingRecordProxyInternal)?._raw) ||
                                deletingRecordsByLocalId.get(localId);
                            if (!usingRecord) {
                                // record already deleted, clean inverses
                                record._.uses.data.delete(localId);
                                continue;
                            }
                            for (let c = 0; c < count; c++) {
                                usingRecord[name2].delete(record);
                            }
                        }
                    }
                    deletingRecordsByLocalId.set(record.localId, record);
                    this.recordByLocalId.delete(record.localId);
                    this._.ADD_QUEUE("hard_delete", toRaw(record));
                }
                while (RHD_QUEUE.size > 0) {
                    // effectively delete the record
                    /** @type {Record} */
                    const record = RHD_QUEUE.keys().next().value;
                    RHD_QUEUE.delete(record);
                    deletingRecordsByLocalId.delete(record.localId);
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
     * @param {T} [dataByModelName={}]
     * @param {Object} [options={}]
     * @returns {{ [K in keyof T]: import("models").Models[K][] }}
     */
    insert(dataByModelName = {}, options = {}) {
        const store = this;
        const ctx = storeInsertFns.makeContext(store);
        Record.MAKE_UPDATE(function storeInsert() {
            const recordsDataToDelete = [];
            for (const [pyOrJsModelName, data] of Object.entries(dataByModelName)) {
                const modelName = storeInsertFns.getActualModelName(store, ctx, pyOrJsModelName);
                if (!store[modelName]) {
                    console.warn(`store.insert() received data for unknown model “${modelName}”.`);
                    continue;
                }
                const insertData = [];
                for (const vals of Array.isArray(data) ? data : [data]) {
                    const extraFields = storeInsertFns.getExtraFieldsFromModel(
                        store,
                        pyOrJsModelName
                    );
                    if (extraFields) {
                        Object.assign(vals, extraFields);
                    }
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
    }
    onChange(record, name, cb) {
        return this._onChange(record, name, (observe) => {
            const fn = () => {
                observe();
                try {
                    cb();
                } catch (err) {
                    this.handleError(err);
                }
            };
            if (this._.UPDATE !== 0) {
                if (!this._.RO_QUEUE.has(fn)) {
                    this._.RO_QUEUE.set(fn, true);
                }
            } else {
                fn();
            }
        });
    }
    /**
     * Version of onChange where the callback receives observe function as param.
     * This is useful when there's desire to postpone calling the callback function,
     * in which the observe is also intended to have its invocation postponed.
     *
     * @param {Record} record
     * @param {string|string[]} key
     * @param {(observe: Function) => any} callback
     * @returns {function} function to call to stop observing changes
     */
    _onChange(record, key, callback) {
        let proxy;
        function _observe() {
            // access proxy[key] only once to avoid triggering reactive get() many times
            const val = proxy[key];
            if (typeof val === "object" && val !== null) {
                void Object.keys(val);
            }
            if (Array.isArray(val)) {
                void val.length;
                void toRaw(val).forEach.call(val, (i) => i);
            }
        }
        if (Array.isArray(key)) {
            for (const k of key) {
                this._onChange(record, k, callback);
            }
            return;
        }
        let ready = true;
        proxy = reactive(record, () => {
            if (ready) {
                callback(_observe);
            }
        });
        _observe();
        return () => {
            ready = false;
        };
    }
    _cleanupData(data) {
        super._cleanupData(data);
        if (this._getActualModelName() === "Store") {
            delete data.Models;
            for (const [name] of modelRegistry.getEntries()) {
                delete data[name];
            }
        }
    }
}
