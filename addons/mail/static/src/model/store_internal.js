/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

import { ManyFieldVersion, SingleFieldVersion, SKIP_REVISION } from "@mail/model/field_version";
import { isCommandList, isMany, normalizeManyCommands, untrackFunctions } from "@mail/model/misc";
import { RecordInternal } from "@mail/model/record_internal";
import { parseRawValue } from "@mail/utils/common/local_storage";
import { incrementFn } from "@mail/utils/common/signal";

import { computed, htmlEscape, markup, signal } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";

const Markup = markup().constructor;

/** @typedef {string} LocalStorageKey */
/** @typedef {string} FieldName */

export class StoreInternal extends RecordInternal {
    /** @type {Map<import("./record").Record, Map<string, true>>} */
    FC_QUEUE = new Map(); // field-computes
    /** @type {Map<import("./record").Record, Map<string, Map<import("./record").Record, true>>>} */
    FA_QUEUE = new Map(); // field-onadds
    /** @type {Map<import("./record").Record, Map<string, Map<import("./record").Record, true>>>} */
    FD_QUEUE = new Map(); // field-ondeletes
    /** @type {Map<import("./record").Record, Map<string, true>>} */
    FU_QUEUE = new Map(); // field-onupdates
    /** @type {Map<Record, true>} */
    RD_QUEUE = new Map(); // record-deletes
    ERRORS = [];
    UPDATE = 0;
    /**
     * The owl app this store belongs to, needed by the scope of each of its
     * records.
     *
     * @type {import("@odoo/owl").App}
     */
    app;
    /**
     * Number of update functions currently running, nested included. An owl
     * computed() field holds its last value while one runs, as the relations
     * it reads are written one by one. onAdd, onDelete and onUpdate run
     * outside of them, at depth 0, so they read fresh values.
     */
    updateDepth = signal(0);
    raiseUpdateDepth = incrementFn(this.updateDepth);
    lowerUpdateDepth = incrementFn(this.updateDepth, -1);
    /**
     * Whether an update function is being run. A computed of the depth, so a
     * held field only recomputes when this flips, not on every nested raise.
     */
    isUpdateInProgress = computed(() => this.updateDepth() > 0);
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
    /**
     * Map of local storage keys of fields synced with local storage to the record and field name.
     *
     * @type {Map<LocalStorageKey, Map<Record, FieldName>>}
     */
    localStorageKeyToRecordFields = new Map();

    constructor() {
        super(...arguments);
        untrackFunctions(this, ["lowerUpdateDepth", "raiseUpdateDepth"]);
        this.onStorage = this.onStorage.bind(this);
        browser.addEventListener("storage", this.onStorage);
    }
    /**
     * Indicates whether the current update cycle was triggered by a
     * `storage` event. Used to prevent writing back to the local
     * storage and creating a feedback loop.
     */
    isUpdatingFromStorageEvent = false;
    onStorage(ev) {
        const entryMap = this.localStorageKeyToRecordFields.get(ev.key);
        if (!entryMap) {
            return;
        }
        this.isUpdatingFromStorageEvent = true;
        try {
            for (const [record, fieldName] of entryMap.entries()) {
                if (ev.newValue === null) {
                    record._proxy[fieldName] = record._.fieldsDefault.get(fieldName);
                } else {
                    const parsed = parseRawValue(ev.newValue);
                    if (!parsed) {
                        record._proxy[fieldName] = record._.fieldsDefault.get(fieldName);
                    } else {
                        record._proxy[fieldName] = parsed.value;
                    }
                }
            }
        } finally {
            this.isUpdatingFromStorageEvent = false;
        }
    }

    /**
     * @param {"compute"|"onAdd"|"onDelete"|"onUpdate"} type
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
            case "onAdd": {
                /** @type {[import("./record").Record, string, import("./record").Record]} */
                const [record, fieldName, addedRec] = params;
                const Model = record.Model;
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
        }
    }
    /** @param {RecordList<Record>} recordList */
    sortRecordList(recordList, func) {
        const recordProxies = recordList._.data().map((record) => record._proxy);
        recordProxies.sort(func);
        const records = recordProxies.map((recordProxy) => recordProxy._raw);
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
            Reflect.set(record._proxy[parentFieldName], fieldName, value);
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
        for (const [fieldName, value] of fieldEntries) {
            let version = record._.fieldsVersion.get(fieldName);
            if (!version) {
                version = isMany(record.Model, fieldName)
                    ? new ManyFieldVersion(record.Model)
                    : new SingleFieldVersion();
                record._.fieldsVersion.set(fieldName, version);
            }
            // Always use the server version if provided, the last known version for the
            // field otherwise.
            const revision = this.currentInsertVersion
                ? {
                      snapshot: this.currentInsertVersion.snapshot,
                      isWrite:
                          this.currentInsertVersion.written_fields_by_record?.[
                              record.Model.getName()
                          ]?.[record.id]?.includes(fieldName),
                  }
                : version.lastRevision;
            const normalized = isMany(record.Model, fieldName)
                ? normalizeManyCommands(value)
                : value;
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
            if (record.Model._.fieldsLocalStorage.has(fieldName)) {
                // should immediately write in local storage, for immediately correct next compute
                if (!this.isUpdatingFromStorageEvent) {
                    const lse = record._.fieldsLocalStorage.get(fieldName);
                    if (value === record._.fieldsDefault.get(fieldName)) {
                        lse.remove();
                    } else {
                        lse.set(value);
                    }
                }
            }
            if (!record.Model._.fields.get(fieldName) || record.Model._.fieldsAttr.get(fieldName)) {
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
