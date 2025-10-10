/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

import { markup, toRaw } from "@odoo/owl";
import { RecordInternal } from "./record_internal";
import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";
import { IS_DELETED_SYM, IS_DELETING_SYM, Markup, isCommand, isMany } from "./misc";

export class StoreInternal extends RecordInternal {
    /**
     * Determines whether the inserts are considered trusted or not.
     * Useful to auto-markup html fields when this is set
     */
    trusted = false;
    /** @type {Map<import("./record").Record, Map<string, true>>} */
    FC_QUEUE = new Map(); // field-computes
    /** @type {Map<import("./record").Record, Map<string, true>>} */
    FS_QUEUE = new Map(); // field-sorts
    /** @type {Map<import("./record").Record, Map<string, Map<import("./record").Record, true>>>} */
    FA_QUEUE = new Map(); // field-onadds
    /** @type {Map<import("./record").Record, Map<string, Map<import("./record").Record, true>>>} */
    FD_QUEUE = new Map(); // field-ondeletes
    /** @type {Map<import("./record").Record, Map<string, true>>} */
    FU_QUEUE = new Map(); // field-onupdates
    /** @type {Map<Function, true>} */
    RO_QUEUE = new Map(); // record-onchanges
    /** @type {Map<Record, true>} */
    RD_QUEUE = new Map(); // record-deletes
    /** @type {Map<Record, true>} */
    RHD_QUEUE = new Map(); // record-hard-deletes
    UPDATE = 0;

    /**
     * @param {"compute"|"sort"|"onAdd"|"onDelete"|"onUpdate"|"hard_delete"} type
     * @param {...any} params
     */
    ADD_QUEUE(type, ...params) {
        switch (type) {
            case "delete": {
                /** @type {import("./record").Record} */
                const [record] = params;
                if (!this.RD_QUEUE.has(record)) {
                    this.RD_QUEUE.set(record, true);
                }
                break;
            }
            case "compute": {
                /** @type {[import("./record").Record, string]} */
                const [record, fieldName] = params;
                let recMap = this.FC_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this.FC_QUEUE.set(record, recMap);
                }
                recMap.set(fieldName, true);
                break;
            }
            case "sort": {
                /** @type {[import("./record").Record, string]} */
                const [record, fieldName] = params;
                let recMap = this.FS_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this.FS_QUEUE.set(record, recMap);
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
                let recMap = this.FA_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this.FA_QUEUE.set(record, recMap);
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
                let recMap = this.FD_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this.FD_QUEUE.set(record, recMap);
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
                let recMap = this.FU_QUEUE.get(record);
                if (!recMap) {
                    recMap = new Map();
                    this.FU_QUEUE.set(record, recMap);
                }
                recMap.set(fieldName, true);
                break;
            }
            case "hard_delete": {
                /** @type {import("./record").Record} */
                const [record] = params;
                record._[IS_DELETING_SYM] = true;
                record._[IS_DELETED_SYM] = true;
                delete record.Model.records[record.localId];
                if (!this.RHD_QUEUE.has(record)) {
                    this.RHD_QUEUE.set(record, true);
                }
                break;
            }
        }
    }
    /** @param {RecordList<Record>} recordListFullProxy */
    sortRecordList(recordListFullProxy, func) {
        const recordList = toRaw(recordListFullProxy)._raw;
        // sort on copy of list so that reactive observers not triggered while sorting
        const recordsFullProxy = recordListFullProxy.data.map((localId) =>
            recordListFullProxy._store.recordByLocalId.get(localId)
        );
        recordsFullProxy.sort(func);
        const data = recordsFullProxy.map((recordFullProxy) => toRaw(recordFullProxy)._raw.localId);
        const hasChanged = recordList.data.some((localId, i) => localId !== data[i]);
        if (hasChanged) {
            recordListFullProxy.data = data;
        }
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
        const targetRecord = record._.proxyUsed.has(fieldName) ? record : record._proxy;
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
        if (fieldHtml && this.trusted) {
            shouldChange =
                record[fieldName]?.toString() !== value?.toString() ||
                !(record[fieldName] instanceof Markup);
            newValue = typeof value === "string" ? markup(value) : value;
        }
        if (shouldChange) {
            record._.updatingAttrs.set(fieldName, true);
            targetRecord[fieldName] = newValue;
            record._.updatingAttrs.delete(fieldName);
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
        const recordList = record[fieldName];
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
                            recordList._.addNoinv(recordList, item);
                        } else if (cmd === "DELETE.noinv") {
                            recordList._.deleteNoinv(recordList, item);
                        } else {
                            recordList.delete(item);
                        }
                    }
                } else {
                    if (cmd === "ADD") {
                        recordList.add(cmdData);
                    } else if (cmd === "ADD.noinv") {
                        recordList._.addNoinv(recordList, cmdData);
                    } else if (cmd === "DELETE.noinv") {
                        recordList._.deleteNoinv(recordList, cmdData);
                    } else {
                        recordList.delete(cmdData);
                    }
                }
            }
        } else if ([null, false, undefined].includes(value)) {
            recordList.clear();
        } else if (!Array.isArray(value)) {
            recordList._.assign(recordList, [value]);
        } else {
            recordList._.assign(recordList, value);
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
                recordList._.addNoinv(recordList, cmdData);
            } else if (cmd === "DELETE.noinv") {
                recordList._.deleteNoinv(recordList, cmdData);
            } else {
                recordList.delete(cmdData);
            }
        } else if ([null, false, undefined].includes(value)) {
            recordList.clear();
        } else {
            recordList.add(value);
        }
    }
}
