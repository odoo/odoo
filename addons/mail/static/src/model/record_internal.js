/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

import { IS_RECORD_SYM, isFieldDefinition, isRelation, makeRecordFieldLocalId } from "./misc";
import { RecordList } from "./record_list";
import { computed, toRaw, untrack } from "@odoo/owl";
import { RecordUses } from "./record_uses";
import { LocalStorageEntry } from "@mail/utils/common/local_storage";

export class RecordInternal {
    [IS_RECORD_SYM] = true;
    /**
     * All dispose functions for this record.
     * For the store, this stores the dispose functions of all records.
     * Useful to automatically call the dispose functions when the record is deleted or in-between each tests.
     *
     * @type {Set<Function>}
     */
    disposeFns = new Set();
    // Note: state of fields in Maps rather than object is intentional for improved performance.
    /**
     * On lazy-sorted field, determines whether the field should be (re-)sorted
     * when it's needed (i.e. accessed). Eager sorted fields are immediately re-sorted at end of update cycle,
     * whereas lazy sorted fields wait extra for them being needed.
     *
     * @type {Map<string, boolean>}
     */
    fieldsSortOnNeed = new Map();
    /**
     * On lazy sorted-fields, determines whether this field is needed (i.e. accessed).
     *
     * @type {Map<string, boolean>}
     */
    fieldsSortInNeed = new Map();
    /**
     * For sorted field, determines whether the field is sorting its value.
     *
     * @type {Map<string, boolean>}
     */
    fieldsSorting = new Map();
    /** @type {Map<string, Function>} */
    fieldsComputeComputed = new Map();
    /** @type {Map<string, boolean>} */
    fieldsComputeComputing = new Map();
    /** @type {Map<string, Function>} */
    fieldsSortComputed = new Map();
    /** @type {Map<string, boolean>} */
    fieldsSortComputing = new Map();
    /**
     * Fields that have an `onUpdate` defined. Key is fieldName, Value is function of ongoing `onChange` that can be disposed.
     * Useful to prevent any ongoing onChange and restart if need be.
     *
     * @type {Map<string, Function>}
     */
    fieldsOnUpdateStop = new Map();
    /** @type {Map<string, any>} */
    fieldsDefault = new Map();
    uses = new RecordUses();
    updatingAttrs = new Map();
    proxyUsed = new Map();
    /** @type {string} */
    localId;
    gettingField = false;
    /** @type {Map<string, import("@mail/model/field_version").SingleFieldVersion|import("@mail/model/field_version").ManyFieldVersion>} */
    fieldsVersion = new Map();

    /**
     * For fields that use local storage, this map contains the "ls" object that eases interactions on the related
     * local storage entry. For instance, instead of having to write `browser.localStorage.setItem(EXACT_LOCAL_STORAGE_ENTRY_OF_FIELD, value)`,
     * this "ls" object allow to just write the equivalent expression with `ls.set(value)`
     *
     * @type {Map<string, LocalStorageEntry>}
     */
    fieldsLocalStorage = new Map();

    /**
     * @param {Record} record
     * @param {string} fieldName
     * @param {Record} recordProxy
     */
    prepareField(record, fieldName, recordProxy) {
        const Model = toRaw(record).Model;
        if (isRelation(Model, fieldName)) {
            // Relational fields contain symbols for detection in original class.
            // This constructor is called on genuine records:
            // - 'one' fields => undefined
            // - 'many' fields => RecordList
            // record[name]?.[0] is ONE_SYM or MANY_SYM
            const recordList = new RecordList();
            Object.assign(recordList._, {
                name: fieldName,
                owner: record,
            });
            Object.assign(recordList, {
                _raw: recordList,
                _store: record.store,
            });
            record[fieldName] = recordList;
        } else {
            record[fieldName] = isFieldDefinition(record[fieldName])
                ? record[fieldName].default
                : record[fieldName];
        }
        this.fieldsDefault.set(fieldName, record[fieldName]);
        // register local storage fields
        for (const lsFieldName of Model._.fieldsLocalStorage) {
            const { localStorageKeyToRecordFields } = record.store._;
            const localStorageKey = makeRecordFieldLocalId(record.localId, lsFieldName);
            if (!localStorageKeyToRecordFields.has(localStorageKey)) {
                localStorageKeyToRecordFields.set(localStorageKey, new Map());
            }
            localStorageKeyToRecordFields.get(localStorageKey).set(record, lsFieldName);
            this.fieldsLocalStorage.set(lsFieldName, new LocalStorageEntry(localStorageKey));
        }
        if (Model._.fieldsCompute.get(fieldName)) {
            const fieldComputed = untrack(() =>
                computed(() => {
                    if (this.fieldsComputeComputing.get(fieldName)) {
                        return;
                    }
                    this.fieldsComputeComputing.set(fieldName, true);
                    const store = record.store;
                    let newValue;
                    try {
                        newValue = Model._.fieldsCompute.get(fieldName).call(record._proxy);
                        if (fieldName === "menuThreads") {
                            console.log("AKU - ", newValue);
                        }
                        untrack(() => store._.updateFields(record, { [fieldName]: newValue }));
                    } catch (err) {
                        store.handleError(err);
                    } finally {
                        this.fieldsComputeComputing.delete(fieldName);
                    }
                    return newValue;
                })
            );
            record._.fieldsComputeComputed.set(fieldName, fieldComputed);
        }
        if (Model._.fieldsSort.get(fieldName)) {
            const fieldComputed = untrack(() =>
                computed(() => {
                    if (this.fieldsSortComputing.get(fieldName)) {
                        return;
                    }
                    this.fieldsSortComputing.set(fieldName, true);
                    const store = record._rawStore;
                    const func = Model._.fieldsSort.get(fieldName).bind(record._proxy);
                    if (isRelation(Model, fieldName)) {
                        try {
                            store._.sortRecordList(record._proxy[fieldName]._proxy, func);
                        } catch (err) {
                            store.handleError(err);
                        } finally {
                            this.fieldsSortComputing.delete(fieldName);
                        }
                    } else {
                        record._proxy[fieldName].sort(func);
                    }
                    this.fieldsSortComputing.delete(fieldName);
                })
            );
            record._.fieldsSortComputed.set(fieldName, fieldComputed);
        }
    }

    /**
     * @param {Record} record
     * @param {string} fieldName
     * @param {Record} recordProxy
     */
    prepareFieldOnUpdate(record, fieldName, recordProxy) {
        const Model = toRaw(record).Model;
        const store = Model.store;
        const fn = store._onChange(recordProxy, fieldName, (obs) => {
            if (store._.UPDATE !== 0) {
                untrack(() => store._.ADD_QUEUE("onUpdate", record, fieldName));
            } else {
                this.onUpdate(record, fieldName);
            }
        });
        this.fieldsOnUpdateStop.set(fieldName, fn);
    }

    onUpdate(record, fieldName) {
        const store = record._rawStore;
        const Model = record.Model;
        this.fieldsOnUpdateStop.get(fieldName)?.();
        const recordProxy = record._proxy;
        if (Model._.fieldsOnUpdate.get(fieldName)) {
            untrack(() => {
                try {
                    /**
                     * Forward internal proxy for performance as onUpdate does not
                     * need reactive (observe is called separately).
                     */
                    Model._.fieldsOnUpdate
                        .get(fieldName)
                        .forEach((fn) => fn.call(recordProxy, recordProxy[fieldName]));
                } catch (err) {
                    store.handleError(err);
                }
            });
        }
        this.prepareFieldOnUpdate(record, fieldName, recordProxy);
    }
}
