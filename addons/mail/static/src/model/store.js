import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";
import { Record } from "./record";
import { IS_DELETED_SYM, Markup, isCommand, isMany, isRecord } from "./misc";
import { markup, reactive, toRaw } from "@odoo/owl";

/** @typedef {import("./record_list").RecordList} RecordList */
/** @typedef {import("./misc").RecordField} RecordField */

export class Store extends Record {
    /** @type {import("./store_internal").StoreInternal} */
    _;

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
        const recordList = record._fields.get(fieldName).value;
        if (isMany(recordList)) {
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
     * @param {RecordField|Record} fieldOrRecord
     * @param {"compute"|"sort"|"onAdd"|"onDelete"|"onUpdate"} type
     * @param {Record} [record] when field with onAdd/onDelete, the record being added or deleted
     */
    ADD_QUEUE(fieldOrRecord, type, record) {
        if (isRecord(fieldOrRecord)) {
            /** @type {Record} */
            const record = fieldOrRecord;
            if (type === "delete") {
                if (!this._.RD_QUEUE.includes(record)) {
                    this._.RD_QUEUE.push(record);
                }
            }
            if (type === "hard_delete") {
                if (!this._.RHD_QUEUE.includes(record)) {
                    this._.RHD_QUEUE.push(record);
                }
            }
        } else {
            /** @type {import("./misc").RecordField} */
            const field = fieldOrRecord;
            const rawField = toRaw(field);
            if (type === "compute") {
                if (!this._.FC_QUEUE.some((f) => toRaw(f) === rawField)) {
                    this._.FC_QUEUE.push(field);
                }
            }
            if (type === "sort") {
                const Model = rawField.value?.owner.Model;
                const sort = Model?._.fieldsSort.get(rawField.name);
                if (!sort) {
                    return;
                }
                if (!this._.FS_QUEUE.some((f) => toRaw(f) === rawField)) {
                    this._.FS_QUEUE.push(field);
                }
            }
            if (type === "onAdd") {
                const Model = rawField.value?.owner.Model;
                const sort = Model?._.fieldsSort.get(rawField.name);
                if (sort) {
                    this.ADD_QUEUE(fieldOrRecord, "sort");
                }
                if (!Model?._.fieldsOnAdd.get(rawField.name)) {
                    return;
                }
                const item = this._.FA_QUEUE.find((item) => toRaw(item.field) === rawField);
                if (!item) {
                    this._.FA_QUEUE.push({ field, records: [record] });
                } else {
                    if (!item.records.some((recordProxy) => recordProxy.eq(record))) {
                        item.records.push(record);
                    }
                }
            }
            if (type === "onDelete") {
                const Model = rawField.value?.owner.Model;
                if (!Model._.fieldsOnDelete.get(rawField.name)) {
                    return;
                }
                const item = this._.FD_QUEUE.find((item) => toRaw(item.field) === rawField);
                if (!item) {
                    this._.FD_QUEUE.push({ field, records: [record] });
                } else {
                    if (!item.records.some((recordProxy) => recordProxy.eq(record))) {
                        item.records.push(record);
                    }
                }
            }
            if (type === "onUpdate") {
                if (!this._.FU_QUEUE.some((f) => toRaw(f) === rawField)) {
                    this._.FU_QUEUE.push(field);
                }
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
                this._.FC_QUEUE.length > 0 ||
                this._.FS_QUEUE.length > 0 ||
                this._.FA_QUEUE.length > 0 ||
                this._.FD_QUEUE.length > 0 ||
                this._.FU_QUEUE.length > 0 ||
                this._.RO_QUEUE.length > 0 ||
                this._.RD_QUEUE.length > 0 ||
                this._.RHD_QUEUE.length > 0
            ) {
                const FC_QUEUE = [...this._.FC_QUEUE];
                const FS_QUEUE = [...this._.FS_QUEUE];
                const FA_QUEUE = [...this._.FA_QUEUE];
                const FD_QUEUE = [...this._.FD_QUEUE];
                const FU_QUEUE = [...this._.FU_QUEUE];
                const RO_QUEUE = [...this._.RO_QUEUE];
                const RD_QUEUE = [...this._.RD_QUEUE];
                const RHD_QUEUE = [...this._.RHD_QUEUE];
                this._.FC_QUEUE.length = 0;
                this._.FS_QUEUE.length = 0;
                this._.FA_QUEUE.length = 0;
                this._.FD_QUEUE.length = 0;
                this._.FU_QUEUE.length = 0;
                this._.RO_QUEUE.length = 0;
                this._.RD_QUEUE.length = 0;
                this._.RHD_QUEUE.length = 0;
                while (FC_QUEUE.length > 0) {
                    const field = FC_QUEUE.pop();
                    field.requestCompute({ force: true });
                }
                while (FS_QUEUE.length > 0) {
                    const field = FS_QUEUE.pop();
                    field.requestSort({ force: true });
                }
                while (FA_QUEUE.length > 0) {
                    const { field, records } = FA_QUEUE.pop();
                    const Model = field.value?.owner.Model;
                    const onAdd = Model._.fieldsOnAdd.get(field.name);
                    records.forEach((record) =>
                        onAdd?.call(field.value.owner._proxy, record._proxy)
                    );
                }
                while (FD_QUEUE.length > 0) {
                    const { field, records } = FD_QUEUE.pop();
                    const Model = field.value?.owner.Model;
                    const onDelete = Model._.fieldsOnDelete.get(field.name);
                    records.forEach((record) =>
                        onDelete?.call(field.value.owner._proxy, record._proxy)
                    );
                }
                while (FU_QUEUE.length > 0) {
                    const field = FU_QUEUE.pop();
                    field.onUpdate();
                }
                while (RO_QUEUE.length > 0) {
                    const cb = RO_QUEUE.pop();
                    cb();
                }
                while (RD_QUEUE.length > 0) {
                    const record = RD_QUEUE.pop();
                    for (const name of record._fields.keys()) {
                        record[name] = undefined;
                    }
                    for (const [localId, names] of record.__uses__.data.entries()) {
                        for (const [name2, count] of names.entries()) {
                            const usingRecordProxy = toRaw(
                                record.Model._rawStore.recordByLocalId
                            ).get(localId);
                            if (!usingRecordProxy) {
                                // record already deleted, clean inverses
                                record.__uses__.data.delete(localId);
                                continue;
                            }
                            const usingRecordList =
                                toRaw(usingRecordProxy)._raw._fields.get(name2).value;
                            if (isMany(usingRecordList)) {
                                for (let c = 0; c < count; c++) {
                                    usingRecordProxy[name2].delete(record);
                                }
                            } else {
                                usingRecordProxy[name2] = undefined;
                            }
                        }
                    }
                    this.ADD_QUEUE(record, "hard_delete");
                }
                while (RHD_QUEUE.length > 0) {
                    const record = RHD_QUEUE.pop();
                    record[IS_DELETED_SYM] = true;
                    delete record.Model.records[record.localId];
                    record.Model._rawStore.recordByLocalId.delete(record.localId);
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
                if (!this._.RO_QUEUE.some((f) => toRaw(f) === fn)) {
                    this._.RO_QUEUE.push(fn);
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
