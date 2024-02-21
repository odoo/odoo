import { markup } from "@odoo/owl";
import { ATTR_SYM, Markup, STORE_SYM, _0, isCommand } from "./misc";
import { RecordInternal } from "./record_internal";
import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";

export class StoreInternal extends RecordInternal {
    /**
     * Determines whether the inserts are considered trusted or not.
     * Useful to auto-markup html fields when this is set
     */
    trusted = false;
    UPDATE = 0;
    /** @type {Object<string, typeof import("./record").Record>} */
    Models;
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
                if (!this.RHD_QUEUE.has(record)) {
                    this.RHD_QUEUE.set(record, true);
                }
                break;
            }
        }
    }
    /**
     * @param {import("./record_list").RecordList} reclist3
     * @param {() => number} func
     */
    sortRecordList(reclist3, func) {
        const reclist0 = _0(reclist3);
        // sort on copy of list so that reactive observers not triggered while sorting
        const records3 = reclist3.value.map((localId) =>
            reclist3._store.localIdToRecord.get(localId)
        );
        records3.sort(func);
        const data = records3.map((record3) => _0(record3).localId);
        const hasChanged = reclist0.value.some((localId, i) => localId !== data[i]);
        if (hasChanged) {
            reclist3.value = data;
        }
    }
    /**
     * @param {import("./record").Record} record
     * @param {Object} vals
     */
    update(record, vals) {
        for (const [fieldName, value] of Object.entries(vals)) {
            if (record?.[STORE_SYM] && fieldName in record._.Models) {
                if (record.storeReady) {
                    // "store[Model] =" is considered a Model.insert()
                    record[fieldName].insert(value);
                } else {
                    record[fieldName] = value;
                }
            } else if (record.Model.INSTANCE_INTERNALS[fieldName]) {
                record[fieldName] = value;
            } else {
                const Model = record.Model;
                if (!Model._.fields.has(fieldName)) {
                    // dynamically add attr field definition on the fly
                    Model._.prepareField(fieldName, { [ATTR_SYM]: true });
                    record._.prepareField(record, fieldName);
                }
                if (Model._.fieldsAttr.has(fieldName)) {
                    this.updateAttr(record, fieldName, value);
                } else {
                    this.updateRelation(record, fieldName, value);
                }
            }
        }
    }
    /**
     * @param {import("./record").Record} record
     * @param {string} fieldName
     * @param {any} value
     */
    updateAttr(record, fieldName, value) {
        const Model = record.Model;
        // ensure each field write goes through the proxy exactly once to trigger reactives
        const record2 = record._.updatingFieldsThroughProxy.has(fieldName) ? record : record._2;
        let shouldChange = record[fieldName] !== value;
        if (Model._.fieldsType.get(fieldName) === "datetime" && value) {
            if (!(value instanceof luxon.DateTime)) {
                value = deserializeDateTime(value);
            }
            shouldChange = !record[fieldName] || !value.equals(record[fieldName]);
        }
        if (Model._.fieldsType.get(fieldName) === "date" && value) {
            if (!(value instanceof luxon.DateTime)) {
                value = deserializeDate(value);
            }
            shouldChange = !record[fieldName] || !value.equals(record[fieldName]);
        }
        let newValue = value;
        if (Model._.fieldsHtml.has(fieldName) && this.trusted) {
            shouldChange =
                record[fieldName]?.toString() !== value?.toString() ||
                !(record[fieldName] instanceof Markup);
            newValue = typeof value === "string" ? markup(value) : value;
        }
        if (shouldChange) {
            const nextTs = Model._.fieldsNextTs.get(fieldName);
            record._.fieldsTs.set(fieldName, nextTs);
            Model._.fieldsNextTs.set(fieldName, nextTs + 1);
            record._.updatingFieldsThroughProxy.add(fieldName);
            record._.updatingAttrs.add(fieldName);
            record2[fieldName] = newValue;
            record._.updatingAttrs.delete(fieldName);
            record._.updatingFieldsThroughProxy.delete(fieldName);
        }
    }
    /**
     * @param {import("./record").Record} record
     * @param {string} fieldName
     * @param {any} value
     */
    updateRelation(record, fieldName, value) {
        /** @type {RecordList} */
        const reclist = record[fieldName];
        if (record.Model._.fieldsMany.get(fieldName)) {
            this.updateRelationMany(reclist, value);
        } else {
            this.updateRelationOne(reclist, value);
        }
    }
    /**
     * @param {import("./record_list").RecordList} reclist
     * @param {any} value
     */
    updateRelationMany(reclist, value) {
        if (isCommand(value)) {
            for (const [cmd, cmdData] of value) {
                if (Array.isArray(cmdData)) {
                    for (const item of cmdData) {
                        if (cmd === "ADD") {
                            reclist.add(item);
                        } else if (cmd === "ADD.noinv") {
                            reclist._.addNoinv(reclist, item);
                        } else if (cmd === "DELETE.noinv") {
                            reclist._.deleteNoinv(reclist, item);
                        } else {
                            reclist.delete(item);
                        }
                    }
                } else {
                    if (cmd === "ADD") {
                        reclist.add(cmdData);
                    } else if (cmd === "ADD.noinv") {
                        reclist._.addNoinv(reclist, cmdData);
                    } else if (cmd === "DELETE.noinv") {
                        reclist._.deleteNoinv(reclist, cmdData);
                    } else {
                        reclist.delete(cmdData);
                    }
                }
            }
        } else if ([null, false, undefined].includes(value)) {
            reclist.clear();
        } else if (!Array.isArray(value)) {
            reclist._.assign(reclist, [value]);
        } else {
            reclist._.assign(reclist, value);
        }
    }
    /**
     * @param {import("./record_list").RecordList} reclist
     * @param {any} value
     * @returns {boolean} whether the value has changed
     */
    updateRelationOne(reclist, value) {
        if (isCommand(value)) {
            const [cmd, cmdData] = value.at(-1);
            if (cmd === "ADD") {
                reclist.add(cmdData);
            } else if (cmd === "ADD.noinv") {
                reclist._.addNoinv(reclist, cmdData);
            } else if (cmd === "DELETE.noinv") {
                reclist._.deleteNoinv(reclist, cmdData);
            } else {
                reclist.delete(cmdData);
            }
        } else if ([null, false, undefined].includes(value)) {
            reclist.clear();
        } else {
            reclist.add(value);
        }
    }
}
