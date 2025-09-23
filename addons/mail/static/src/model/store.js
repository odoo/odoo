import { Record } from "./record";
import { STORE_SYM } from "./misc";
import { reactive, toRaw } from "@odoo/owl";

/** @typedef {import("./record_list").RecordList} RecordList */

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

    /** @param {() => any} fn */
    MAKE_UPDATE(fn) {
        this._.UPDATE++;
        const res = fn();
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
                            onAdd?.call(record._proxy, addedRec._proxy);
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
                            onDelete?.call(record._proxy, removedRec._proxy);
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
                    cb();
                }
                while (RD_QUEUE.size > 0) {
                    /** @type {Record} */
                    const record = RD_QUEUE.keys().next().value;
                    RD_QUEUE.delete(record);
                    for (const [localId, names] of record._.uses.data.entries()) {
                        for (const [name2, count] of names.entries()) {
                            const usingRecord2 =
                                toRaw(this.recordByLocalId).get(localId) ||
                                deletingRecordsByLocalId.get(localId);
                            if (!usingRecord2) {
                                // record already deleted, clean inverses
                                record._.uses.data.delete(localId);
                                continue;
                            }
                            if (usingRecord2.Model._.fieldsMany.get(name2)) {
                                for (let c = 0; c < count; c++) {
                                    usingRecord2[name2].delete(record);
                                }
                            } else {
                                usingRecord2[name2] = undefined;
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
        }
        return res;
    }
    onChange(record, name, cb) {
        return this._onChange(record, name, (observe) => {
            const fn = () => {
                observe();
                cb();
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
}
