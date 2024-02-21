import { reactive, toRaw } from "@odoo/owl";
import { Record } from "./record";
import { RECORD_DELETED_SYM, STORE_SYM, _0 } from "./misc";

export class Store extends Record {
    /** @type {import("./store_internal").StoreInternal} */
    _;
    static singleton = true;
    /** @type {Map<string, string>} */
    objectIdToLocalId;
    /** @type {Map<string, Record>} */
    localIdToRecord;
    [STORE_SYM] = true;
    /**
     * should be called in 0-mode!
     *
     * @param {() => any} fn
     */
    MAKE_UPDATE(fn) {
        this._.UPDATE++;
        const res = fn();
        this._.UPDATE--;
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
                    const [record, recMap] = FC_QUEUE.entries().next().value;
                    FC_QUEUE.delete(record);
                    for (const fieldName of recMap.keys()) {
                        record._.requestComputeField(record, fieldName, { force: true });
                    }
                }
                while (FS_QUEUE.size > 0) {
                    const [record, recMap] = FS_QUEUE.entries().next().value;
                    FS_QUEUE.delete(record);
                    for (const fieldName of recMap.keys()) {
                        record._.requestSortField(record, fieldName, { force: true });
                    }
                }
                while (FA_QUEUE.size > 0) {
                    const [record, recMap] = FA_QUEUE.entries().next().value;
                    FA_QUEUE.delete(record);
                    while (recMap.size > 0) {
                        const [fieldName, fieldMap] = recMap.entries().next().value;
                        recMap.delete(fieldName);
                        const onAdd = record.Model._.fieldsOnAdd.get(fieldName);
                        for (const addedRec of fieldMap.keys()) {
                            onAdd?.call(record._2, addedRec._2);
                        }
                    }
                }
                while (FD_QUEUE.size > 0) {
                    const [record, recMap] = FD_QUEUE.entries().next().value;
                    FD_QUEUE.delete(record);
                    while (recMap.size > 0) {
                        const [fieldName, fieldMap] = recMap.entries().next().value;
                        recMap.delete(fieldName);
                        const onDelete = record.Model._.fieldsOnDelete.get(fieldName);
                        for (const removedRec of fieldMap.keys()) {
                            onDelete?.call(record._2, removedRec._2);
                        }
                    }
                }
                while (FU_QUEUE.size > 0) {
                    const [record, map] = FU_QUEUE.entries().next().value;
                    FU_QUEUE.delete(record);
                    for (const fieldName of map.keys()) {
                        record._.onUpdateField(record, fieldName);
                    }
                }
                while (RO_QUEUE.size > 0) {
                    const cb = RO_QUEUE.keys().next().value;
                    RO_QUEUE.delete(cb);
                    cb();
                }
                while (RD_QUEUE.size > 0) {
                    const record = RD_QUEUE.keys().next().value;
                    RD_QUEUE.delete(record);
                    for (const [localId, names] of record._.uses.data.entries()) {
                        for (const [name2, count] of names.entries()) {
                            const usingRecord2 = _0(this.localIdToRecord).get(localId);
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
                    this._.ADD_QUEUE(record, "hard_delete");
                }
                while (RHD_QUEUE.size > 0) {
                    // effectively delete the record
                    const record = RHD_QUEUE.keys().next().value;
                    RD_QUEUE.delete(record);
                    record[RECORD_DELETED_SYM] = true;
                    for (const objectId of record._.objectIds) {
                        this.objectIdToLocalId.delete(objectId);
                    }
                    for (const localId of record._.localIds) {
                        delete record.Model.records[localId];
                        this.localIdToRecord.delete(localId);
                    }
                }
            }
            this._.UPDATE--;
        }
        return res;
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
    // Internal props on instance. Important to not have them being registered as fields!
    static get INSTANCE_INTERNALS() {
        return {
            ...super.INSTANCE_INTERNALS,
            localIdToRecord: true,
            objectIdToLocalId: true,
            storeReady: true,
        };
    }
    storeReady = false;
    /**
     * @param {string} objectId
     * @returns {Record}
     */
    get(objectId) {
        return this.localIdToRecord.get(this.objectIdToLocalId.get(objectId));
    }
}
