/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */
/** @typedef {import("./store").Store} Store */

import { ManyFieldVersion, SingleFieldVersion, SKIP_REVISION } from "@mail/model/field_version";
import {
    isCommandList,
    isMany,
    normalizeManyCommands,
    technicalKeysOnRecords,
    untrackFunctions,
} from "@mail/model/misc";
import { RecordInternal } from "@mail/model/record_internal";

import { htmlEscape, markup, signal } from "@odoo/owl";

import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";

const Markup = markup().constructor;

export class StoreInternal extends RecordInternal {
    /**
     * See {@link StoreInternal#MAKE_UPDATE}.
     * @type {Map<Record, true>}
     */
    RD_QUEUE = new Map(); // record-deletes
    /**
     * See {@link StoreInternal#MAKE_UPDATE}. One level per running onChange, for what it
     * queues: the top one runs first, after the field computes of every level.
     * @type {{ computes: Set<() => void>, others: Set<() => void> }[]}
     */
    OC_QUEUE = [{ computes: new Set(), others: new Set() }]; // immediate onChanges
    /** @type {Map<() => void, Set<() => void>>} */
    OC_QUEUED = new Map();
    /** See {@link StoreInternal#MAKE_UPDATE}. */
    isRunningOnChanges = false;
    /** See {@link StoreInternal#MAKE_UPDATE}. */
    ERRORS = [];
    /** See {@link StoreInternal#MAKE_UPDATE}. */
    UPDATE = 0;
    /**
     * The owl app this store belongs to, needed by the scope of each of its
     * records.
     *
     * @type {import("@odoo/owl").App}
     */
    app;
    /** See {@link StoreInternal#MAKE_UPDATE}. */
    updateDepth = 0;
    /**
     * Written only when the depth leaves or comes back to 0, so a held field
     * is not notified on every nested raise. See {@link StoreInternal#MAKE_UPDATE}.
     */
    isUpdateInProgress = signal(false);
    /** See {@link StoreInternal#MAKE_UPDATE}. */
    isDrainingQueues = false;
    /** See {@link StoreInternal#MAKE_UPDATE}. */
    warnErrors = true;
    /**
     * Current version context used in the current store insert operation.
     *
     * The version data is provided by the server. If no version is provided,
     * each field falls back to its last known version.
     *
     * @type {{
     *    written_fields_by_record: import("@mail/model/field_version").WrittenFieldsByRecord,
     *    snapshot: import("@mail/model/field_version").PgSnapshot
     * }}
     */
    currentInsertVersion = null;

    raiseUpdateDepth() {
        if (this.updateDepth++ === 0) {
            this.isUpdateInProgress.set(true);
        }
    }
    lowerUpdateDepth() {
        if (--this.updateDepth === 0) {
            this.isUpdateInProgress.set(false);
        }
    }
    /**
     * Run `fn` as one update of the store, so that the rest of the app sees
     * everything `fn` writes as a single change.
     *
     * A write sets fields and relations one by one, so the data is only
     * consistent once the whole update is done. Until then:
     * - A computed field keeps its last value rather than computing one from
     *   half written data (`isUpdateInProgress`).
     * - The record deletions that the writes ask for wait in `RD_QUEUE`, to
     *   run once at the end.
     * - An immediate onChange waits in `OC_QUEUE`, run after the deletions,
     *   so it sees the final values. The field computes run first, so the
     *   others see their values.
     * - An error does not leave the store in the middle of an update: it goes
     *   to `ERRORS`, the update still ends, and then the first error is thrown.
     *
     * An update started inside another update joins the outer one (`UPDATE`,
     * `updateDepth`): only the outermost update runs the queues.
     *
     * A write of a record deletion does not raise `updateDepth`: computeds
     * already run unheld between its writes, and raising it would wake every
     * held computed twice per write. A write of a queued onChange raises it,
     * as its callback may insert records that other computeds read.
     *
     * @param {() => any} fn
     */
    MAKE_UPDATE(fn) {
        const isDrainWrite = this.UPDATE !== 0 && this.isDrainingQueues && !this.isRunningOnChanges;
        if (!isDrainWrite) {
            this.raiseUpdateDepth();
        }
        this.UPDATE++;
        let res;
        try {
            res = fn();
        } catch (err) {
            this.ERRORS.push(err);
        }
        this.UPDATE--;
        if (this.UPDATE === 0) {
            this.isDrainingQueues = true;
        }
        if (!isDrainWrite) {
            this.lowerUpdateDepth();
        }
        if (this.UPDATE === 0) {
            // pretend an increased update cycle so that nothing in queue creates many small update cycles
            this.UPDATE++;
            while (this.RD_QUEUE.size > 0 || this.OC_QUEUED.size > 0) {
                const RD_QUEUE = new Map(this.RD_QUEUE);
                this.RD_QUEUE.clear();
                while (RD_QUEUE.size > 0) {
                    /** @type {Record} */
                    const record = RD_QUEUE.keys().next().value;
                    RD_QUEUE.delete(record);
                    record._.isDeleted.set(true);
                    record._.scope?.destroy();
                    record.Model.records.delete(record.localId);
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
                        recordList._.data.set([]);
                    }
                }
                // One at a time, so that what it queues and deletes runs before the next one.
                const runOnChange = this.nextOnChange();
                if (runOnChange) {
                    this.isRunningOnChanges = true;
                    runOnChange();
                    this.isRunningOnChanges = false;
                }
            }
            this.OC_QUEUE.splice(1);
            this.UPDATE--;
            this.isDrainingQueues = false;
            if (this.ERRORS.length) {
                if (this.warnErrors) {
                    console.warn("Store data insert aborted due to following errors:");
                    for (const err of this.ERRORS) {
                        console.warn(err);
                    }
                }
                const [error1] = this.ERRORS;
                this.ERRORS = [];
                throw error1;
            }
        }
        return res;
    }

    /**
     * @param {"change"|"delete"} type
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
            case "change": {
                const [runOnChange, isCompute] = params;
                const level = this.OC_QUEUE.at(-1);
                const queue = isCompute ? level.computes : level.others;
                this.OC_QUEUED.get(runOnChange)?.delete(runOnChange);
                queue.add(runOnChange);
                this.OC_QUEUED.set(runOnChange, queue);
                break;
            }
        }
    }
    /** @returns {(() => void)|undefined} the next queued onChange, with a new level for what it queues */
    nextOnChange() {
        let level = this.OC_QUEUE.at(-1);
        while (level.computes.size === 0 && level.others.size === 0 && this.OC_QUEUE.length > 1) {
            this.OC_QUEUE.pop();
            level = this.OC_QUEUE.at(-1);
        }
        const computeLevel = this.OC_QUEUE.findLast((l) => l.computes.size > 0);
        const queue = computeLevel ? computeLevel.computes : level.others;
        const [runOnChange] = queue;
        if (!runOnChange) {
            return;
        }
        queue.delete(runOnChange);
        this.OC_QUEUED.delete(runOnChange);
        this.OC_QUEUE.push({ computes: new Set(), others: new Set() });
        return runOnChange;
    }
    /** @param {RecordList<Record>} recordList */
    sortRecordList(recordList, func) {
        const records = recordList._.data().slice();
        records.sort(func);
        const hasChanged = recordList._.data().some((record, i) => record !== records[i]);
        if (hasChanged) {
            recordList._.data.set(records);
        }
    }
    /**
     * @param {Record} record
     * @param {string} fieldName
     * @param {any} value
     */
    updateAttr(record, fieldName, value) {
        const Model = record.Model;
        const parentFieldName = Model._.parentFields.get(fieldName);
        if (parentFieldName) {
            // Route the write to the parent record, which stores an _inherits field.
            Reflect.set(record[parentFieldName], fieldName, value);
            return;
        }
        if (Model._.fieldsComputable.has(fieldName)) {
            console.warn(`${Model.getName()}.${fieldName} is computed: dropping the write.`);
            return;
        }
        const fieldType = Model._.fieldsType.get(fieldName);
        const fieldHtml = Model._.fieldsHtml.get(fieldName);
        const sig = record._.ensureFieldSignal(fieldName);
        const current = sig();
        let shouldChange = current !== value;
        if (fieldType === "datetime" && value) {
            if (!(value instanceof luxon.DateTime)) {
                value = deserializeDateTime(value);
            }
            shouldChange = !current || !value.equals(current);
        }
        if (fieldType === "date" && value) {
            if (!(value instanceof luxon.DateTime)) {
                value = deserializeDate(value);
            }
            shouldChange = !current || !value.equals(current);
        }
        let newValue = value;
        if (fieldHtml) {
            newValue =
                Array.isArray(value) && value[0] === "markup"
                    ? value[1]
                        ? markup(value[1])
                        : ""
                    : value
                    ? htmlEscape(value)
                    : "";
            shouldChange =
                current?.toString() !== newValue?.toString() ||
                current instanceof Markup != newValue instanceof Markup;
        }
        if (shouldChange) {
            sig.set(newValue);
        }
    }
    /**
     * @param {Record} record
     * @param {Object} vals
     * @param {Object} [options={}]
     * @param {boolean} [options.forceApply=true] Apply the values even when the
     * current insert version is out of order. Only versioned server data turns
     * it off.
     */
    updateFields(record, vals, { forceApply = true } = {}) {
        const fieldEntries = Object.entries(vals).concat(
            Object.getOwnPropertySymbols(vals).map((sym) => [sym, vals[sym]])
        );
        const Model = record.Model;
        const recordInternal = record._;
        for (const [fieldName, value] of fieldEntries) {
            if (typeof fieldName === "string" && Model._.parentFields.get(fieldName)) {
                record[fieldName] = value;
                continue;
            }
            if (
                typeof fieldName === "string" &&
                !Model._.fields.get(fieldName) &&
                !Model._.fieldsComputable.has(fieldName) &&
                !technicalKeysOnRecords.has(fieldName)
            ) {
                console.warn(
                    `Dropping unknown field "${fieldName}" inserted on "${Model.getName()}": records only hold declared fields.`
                );
                continue;
            }
            let version = recordInternal.fieldsVersion.get(fieldName);
            if (!version) {
                version = isMany(Model, fieldName)
                    ? new ManyFieldVersion(Model)
                    : new SingleFieldVersion();
                recordInternal.fieldsVersion.set(fieldName, version);
            }
            // Always use the server version if provided, the last known version for the
            // field otherwise.
            const revision = this.currentInsertVersion
                ? {
                      snapshot: this.currentInsertVersion.snapshot,
                      isWrite:
                          this.currentInsertVersion.written_fields_by_record?.[Model.getName()]?.[
                              record.id
                          ]?.includes(fieldName),
                  }
                : version.lastRevision;
            const normalized = isMany(Model, fieldName) ? normalizeManyCommands(value) : value;
            // ".noinv" commands only come from inverse echoes: they are
            // client-generated even when found inside server data to insert.
            const toApply = version.resolveApply(normalized, revision, {
                forceApply:
                    forceApply ||
                    (isCommandList(normalized) &&
                        normalized.every(([mode]) => mode.endsWith(".noinv"))),
            });
            if (toApply === SKIP_REVISION) {
                continue;
            }
            if (!Model._.fields.get(fieldName) || Model._.fieldsAttr.get(fieldName)) {
                this.updateAttr(record, fieldName, toApply);
            } else {
                this.updateRelation(record, fieldName, toApply);
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
        const recordList = record._.fieldsList.get(fieldName);
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
        for (const [cmd, cmdData] of value) {
            if (cmd === "REPLACE") {
                recordList._.assign(cmdData);
                continue;
            }
            for (const item of cmdData) {
                switch (cmd) {
                    case "ADD":
                        recordList.add(item);
                        break;
                    case "ADD.noinv":
                        recordList._.addNoinv(item);
                        break;
                    case "DELETE":
                        recordList.delete(item);
                        break;
                    case "DELETE.noinv":
                        recordList._.deleteNoinv(item);
                        break;
                }
            }
        }
    }
    /**
     * @param {RecordList} recordList
     * @param {any} value
     * @returns {boolean} whether the value has changed
     */
    updateRelationOne(recordList, value) {
        if (isCommandList(value)) {
            const [cmd, cmdData] = value.at(-1);
            if (["ADD", "REPLACE"].includes(cmd)) {
                recordList.add(cmdData);
            } else if (cmd === "ADD.noinv") {
                recordList._.addNoinv(cmdData);
            } else if (cmd === "DELETE.noinv") {
                recordList._.deleteNoinv(cmdData);
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

untrackFunctions(StoreInternal.prototype, [
    "updateAttr",
    "updateFields",
    "updateRelation",
    "updateRelationMany",
    "updateRelationOne",
]);
