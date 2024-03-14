import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";
import { Record } from "./record";
import { IS_DELETED_SYM, Markup, STORE_SYM, isCommand, isMany } from "./misc";
import { markup, reactive, toRaw } from "@odoo/owl";

/** @typedef {import("./record_list").RecordList} RecordList */
/** @typedef {import("./misc").RecordField} RecordField */

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

    /**
     * @param {Record} record
     * @param {string} fieldName
     * @param {any} value
     */
    updateAttr(record, fieldName, value) {
        const Model = record.Model;
        const fieldType = Model._.fieldsType.get(fieldName);
        const fieldHtml = Model._.fieldsHtml.get(fieldName);
        // ensure each field write goes through the proxy exactly once to trigger reactives
        const targetRecord = record._proxyUsed.has(fieldName) ? record : record._proxy;
        let shouldChange = record[fieldName] !== value;
        if (fieldType === "datetime" && value) {
            if (!(value instanceof luxon.DateTime)) {
                value = deserializeDateTime(value);
            }
            shouldChange = !record[fieldName] || !value.equals(record[fieldName]);
        }
        if (fieldType === "date" && value) {
            if (!(value instanceof luxon.DateTime)) {
                value = deserializeDate(value);
            }
            shouldChange = !record[fieldName] || !value.equals(record[fieldName]);
        }
        let newValue = value;
        if (fieldHtml && this._.trusted) {
            shouldChange =
                record[fieldName]?.toString() !== value?.toString() ||
                !(record[fieldName] instanceof Markup);
            newValue = typeof value === "string" ? markup(value) : value;
        }
        if (shouldChange) {
            record._updateFields.add(fieldName);
            targetRecord[fieldName] = newValue;
            record._updateFields.delete(fieldName);
        }
    }
    /**
     * @param {Record} record
     * @param {Object} vals
     */
    updateFields(record, vals) {
        for (const [fieldName, value] of Object.entries(vals)) {
            if (!record.Model._.fields.get(fieldName) || record.Model._.fieldsAttr.get(fieldName)) {
                this.updateAttr(record, fieldName, value);
            } else {
                this.updateRelation(record, fieldName, value);
            }
        }
    }
    /**
     * @param {Record} record
     * @param {string} fieldName
     * @param {any} value
     */
    updateRelation(record, fieldName, value) {
        /** @type {RecordList<Record>} */
        const recordList = record._fieldsValue.get(fieldName);
        if (isMany(record.Model, fieldName)) {
            this.updateRelationMany(recordList, value);
        } else {
            this.updateRelationOne(recordList, value);
        }
    }
    /**
     * @param {RecordList} recordList
     * @param {any} value
     */
    updateRelationMany(recordList, value) {
        if (isCommand(value)) {
            for (const [cmd, cmdData] of value) {
                if (Array.isArray(cmdData)) {
                    for (const item of cmdData) {
                        if (cmd === "ADD") {
                            recordList.add(item);
                        } else if (cmd === "ADD.noinv") {
                            recordList._addNoinv(item);
                        } else if (cmd === "DELETE.noinv") {
                            recordList._deleteNoinv(item);
                        } else {
                            recordList.delete(item);
                        }
                    }
                } else {
                    if (cmd === "ADD") {
                        recordList.add(cmdData);
                    } else if (cmd === "ADD.noinv") {
                        recordList._addNoinv(cmdData);
                    } else if (cmd === "DELETE.noinv") {
                        recordList._deleteNoinv(cmdData);
                    } else {
                        recordList.delete(cmdData);
                    }
                }
            }
        } else if ([null, false, undefined].includes(value)) {
            recordList.clear();
        } else if (!Array.isArray(value)) {
            recordList.assign([value]);
        } else {
            recordList.assign(value);
        }
    }
    /**
     * @param {RecordList} recordList
     * @param {any} value
     * @returns {boolean} whether the value has changed
     */
    updateRelationOne(recordList, value) {
        if (isCommand(value)) {
            const [cmd, cmdData] = value.at(-1);
            if (cmd === "ADD") {
                recordList.add(cmdData);
            } else if (cmd === "ADD.noinv") {
                recordList._addNoinv(cmdData);
            } else if (cmd === "DELETE.noinv") {
                recordList._deleteNoinv(cmdData);
            } else {
                recordList.delete(cmdData);
            }
        } else if ([null, false, undefined].includes(value)) {
            recordList.clear();
        } else {
            recordList.add(value);
        }
    }
    /** @param {RecordList<Record>} recordListFullProxy */
    sortRecordList(recordListFullProxy, func) {
        const recordList = toRaw(recordListFullProxy)._raw;
        // sort on copy of list so that reactive observers not triggered while sorting
        const recordsFullProxy = recordListFullProxy.data.map((localId) =>
            recordListFullProxy.store.recordByLocalId.get(localId)
        );
        recordsFullProxy.sort(func);
        const data = recordsFullProxy.map((recordFullProxy) => toRaw(recordFullProxy)._raw.localId);
        const hasChanged = recordList.data.some((localId, i) => localId !== data[i]);
        if (hasChanged) {
            recordListFullProxy.data = data;
        }
    }
    /**
     * @param {"compute"|"sort"|"onAdd"|"onDelete"|"onUpdate"|"hard_delete"} type
     * @param {...any} params
     */
    ADD_QUEUE(type, ...params) {
        switch (type) {
            case "delete": {
                /** @type {import("./record").Record} */
                const [record] = params;
                if (!this._.RD_QUEUE.has(record)) {
                    this._.RD_QUEUE.set(record, true);
                }
                break;
            }
            case "compute": {
                /** @type {[import("./record").Record, string]} */
                const [record, fieldName] = params;
                let recMap = this._.FC_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this._.FC_QUEUE.set(record, recMap);
                }
                recMap.set(fieldName, true);
                break;
            }
            case "sort": {
                /** @type {[import("./record").Record, string]} */
                const [record, fieldName] = params;
                let recMap = this._.FS_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this._.FS_QUEUE.set(record, recMap);
                }
                recMap.set(fieldName, true);
                break;
            }
            case "onAdd": {
                /** @type {[import("./record").Record, string, import("./record").Record]} */
                const [record, fieldName, addedRec] = params;
                const Model = record.Model;
                if (Model._.fieldsSort.get(fieldName)) {
                    this.ADD_QUEUE("sort", record, fieldName);
                }
                if (!Model._.fieldsOnAdd.get(fieldName)) {
                    return;
                }
                let recMap = this._.FA_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this._.FA_QUEUE.set(record, recMap);
                }
                let fieldMap = recMap.get(fieldName);
                if (!fieldMap) {
                    fieldMap = new Map();
                    recMap.set(fieldName, fieldMap);
                }
                fieldMap.set(addedRec, true);
                break;
            }
            case "onDelete": {
                /** @type {[import("./record").Record, string, import("./record").Record]} */
                const [record, fieldName, removedRec] = params;
                const Model = record.Model;
                if (!Model._.fieldsOnDelete.get(fieldName)) {
                    return;
                }
                let recMap = this._.FD_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this._.FD_QUEUE.set(record, recMap);
                }
                let fieldMap = recMap.get(fieldName);
                if (!fieldMap) {
                    fieldMap = new Map();
                    recMap.set(fieldName, fieldMap);
                }
                fieldMap.set(removedRec, true);
                break;
            }
            case "onUpdate": {
                /** @type {[import("./record").Record, string]} */
                const [record, fieldName] = params;
                let recMap = this._.FU_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this._.FU_QUEUE.set(record, recMap);
                }
                recMap.set(fieldName, true);
                break;
            }
            case "hard_delete": {
                /** @type {import("./record").Record} */
                const [record] = params;
                if (!this._.RHD_QUEUE.has(record)) {
                    this._.RHD_QUEUE.set(record, true);
                }
                break;
            }
        }
    }
    /** @param {() => any} fn */
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
                    for (const [localId, names] of record.__uses__.data.entries()) {
                        for (const [name2, count] of names.entries()) {
                            const usingRecord2 = toRaw(this.recordByLocalId).get(localId);
                            if (!usingRecord2) {
                                // record already deleted, clean inverses
                                record.__uses__.data.delete(localId);
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
                    this.ADD_QUEUE("hard_delete", toRaw(record));
                }
                while (RHD_QUEUE.size > 0) {
                    // effectively delete the record
                    /** @type {Record} */
                    const record = RHD_QUEUE.keys().next().value;
                    RHD_QUEUE.delete(record);
                    record._[IS_DELETED_SYM] = true;
                    delete record.Model.records[record.localId];
                    this.recordByLocalId.delete(record.localId);
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
