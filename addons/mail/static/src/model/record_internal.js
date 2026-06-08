/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

import {
    IS_DELETED_SYM,
    IS_RECORD_SYM,
    isFieldDefinition,
    isRelation,
    makeRecordFieldLocalId,
} from "./misc";
import { RecordList } from "./record_list";
import { immediateEffect, toRaw, untrack } from "@odoo/owl";
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
     * For computed field, determines whether the field is computing its value.
     *
     * @type {Map<string, boolean>}
     */
    fieldsComputing = new Map();
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
    /**
     * On lazy computed-fields, determines whether this field is needed (i.e. accessed).
     *
     * @type {Map<string, boolean>}
     */
    fieldsComputeInNeed = new Map();
    /**
     * on lazy-computed field, determines whether the field should be (re-)computed
     * when it's needed (i.e. accessed). Eager computed fields are immediately re-computed at end of update cycle,
     * whereas lazy computed fields wait extra for them being needed.
     *
     * @type {Map<string, boolean>}
     */
    fieldsComputeOnNeed = new Map();
    /**
     * Fields that have an `compute` defined. Key is fieldName, Value is function of ongoing `immediateEffect` that let it stop.
     * Useful to prevent any ongoing `immediateEffect` and restart if need be.
     *
     * @type {Map<string, Function>}
     */
    fieldsComputeStop = new Map();
    /**
     * Fields that have an `onUpdate` defined. Key is fieldName, Value is function of ongoing `onChange` that can be disposed.
     * Useful to prevent any ongoing onChange and restart if need be.
     *
     * @type {Map<string, Function>}
     */
    fieldsOnUpdateStop = new Map();
    /**
     * Fields that have an `sort` defined. Key is fieldName, Value is function of ongoing `immediateEffect` that let it stop.
     * Useful to prevent any ongoing `immediateEffect` and restart if need be.
     *
     * @type {Map<string, Function>}
     */
    fieldsSortStop = new Map();
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
            if (!Model._.fieldsEager.get(fieldName)) {
                record.registerOnChange(recordProxy, fieldName, () => {
                    if (this.fieldsComputing.get(fieldName)) {
                        /**
                         * Use a reactive to reset the computeInNeed flag when there is
                         * a change. This assumes when other reactive are still
                         * observing the value, its own callback will reset the flag to
                         * true through the proxy getters.
                         */
                        this.fieldsComputeInNeed.delete(fieldName);
                    }
                });
                // reset flags triggered by registering onChange
                this.fieldsComputeInNeed.delete(fieldName);
                this.fieldsSortInNeed.delete(fieldName);
            }
        }
        if (Model._.fieldsSort.get(fieldName)) {
            if (!Model._.fieldsEager.get(fieldName)) {
                record.registerOnChange(recordProxy, fieldName, () => {
                    if (this.fieldsSorting.get(fieldName)) {
                        /**
                         * Use a reactive to reset the inNeed flag when there is a
                         * change. This assumes if another reactive is still observing
                         * the value, its own callback will reset the flag to true
                         * through the proxy getters.
                         */
                        this.fieldsSortInNeed.delete(fieldName);
                    }
                });
                // reset flags triggered by registering onChange
                this.fieldsComputeInNeed.delete(fieldName);
                this.fieldsSortInNeed.delete(fieldName);
            }
        }
        if (Model._.fieldsOnUpdate.get(fieldName)) {
            this.prepareFieldOnUpdate(record, fieldName, recordProxy);
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

    requestCompute(record, fieldName, { force = false } = {}) {
        if (record[IS_DELETED_SYM]) {
            return;
        }
        const Model = record.Model;
        if (!Model._.fieldsCompute.get(fieldName)) {
            return;
        }
        const store = record._rawStore;
        if (store._.UPDATE !== 0 && !force) {
            store._.ADD_QUEUE("compute", record, fieldName);
        } else {
            if (Model._.fieldsEager.get(fieldName) || this.fieldsComputeInNeed.get(fieldName)) {
                this.compute(record, fieldName);
            } else {
                this.fieldsComputeOnNeed.set(fieldName, true);
            }
        }
    }
    requestSort(record, fieldName, { force } = {}) {
        if (record[IS_DELETED_SYM]) {
            return;
        }
        const Model = record.Model;
        if (!Model._.fieldsSort.get(fieldName)) {
            return;
        }
        const store = record._rawStore;
        if (store._.UPDATE !== 0 && !force) {
            store._.ADD_QUEUE("sort", record, fieldName);
        } else {
            if (Model._.fieldsEager.get(fieldName) || this.fieldsSortInNeed.get(fieldName)) {
                this.sort(record, fieldName);
            } else {
                this.fieldsSortOnNeed.set(fieldName, true);
            }
        }
    }
    /**
     * @param {Record} record
     * @param {string} fieldName
     * @param {Object} [param2={}]
     * @param {boolean} [param2.fromInNeed] whether the compute is triggered from an "in-need" observer.
     *  Useful to force keeping the "in-need" flag, as the "in-need" is automatically reset whenever a computing value has changed.
     *  The "in-need" flag is expected to be set again by observed on the next read, but if the compute is immediately triggered
     *  by the "in-need" then that's the case the `fromInNeed: true` and it should preserve for this ongoing compute.
     */
    compute(record, fieldName, { fromInNeed } = {}) {
        const Model = record.Model;
        if (!Model._.fieldsCompute.get(fieldName)) {
            return;
        }
        const prevStopFn = this.fieldsComputeStop.get(fieldName);
        if (prevStopFn) {
            record._runDisposeFn(prevStopFn);
        }
        let triggered = false;
        const stopFn = untrack(() =>
            immediateEffect(() => {
                if (triggered) {
                    return untrack(() => this.requestCompute(record, fieldName));
                }
                const store = record._rawStore;
                this.fieldsComputing.set(fieldName, true);
                this.fieldsComputeOnNeed.delete(fieldName);
                let computedValue;
                try {
                    computedValue = Model._.fieldsCompute.get(fieldName).call(record._proxy);
                } catch (err) {
                    store.handleError(err);
                }
                untrack(() =>
                    store._.updateFields(record, {
                        [fieldName]: computedValue,
                    })
                );
                this.fieldsComputing.delete(fieldName);
            })
        );
        this.fieldsComputeStop.set(fieldName, stopFn);
        record._registerDisposeFn(stopFn);
        if (fromInNeed) {
            this.fieldsComputeInNeed.set(fieldName, true);
        }
        triggered = true;
    }
    /**
     * @param {Record} record
     * @param {string} fieldName
     * @param {Object} [param2={}]
     * @param {boolean} [param2.fromInNeed] whether the sort is triggered from an "in-need" observer.
     *  Useful to force keeping the "in-need" flag, as the "in-need" is automatically reset whenever a sorting value has changed.
     *  The "in-need" flag is expected to be set again by observed on the next read, but if the sort is immediately triggered
     *  by the "in-need" then that's the case the `fromInNeed: true` and it should preserve for this ongoing sort.
     */
    sort(record, fieldName, { fromInNeed } = {}) {
        const Model = record.Model;
        if (!Model._.fieldsSort.get(fieldName)) {
            return;
        }
        const prevStopFn = this.fieldsSortStop.get(fieldName);
        if (prevStopFn) {
            record._runDisposeFn(prevStopFn);
        }
        let triggered = false;
        const stopFn = untrack(() =>
            immediateEffect(() => {
                if (triggered) {
                    return untrack(() => this.requestSort(record, fieldName));
                }
                const store = record._rawStore;
                this.fieldsSortOnNeed.delete(fieldName);
                this.fieldsSorting.set(fieldName, true);
                const func = Model._.fieldsSort.get(fieldName).bind(record._proxy);
                if (isRelation(Model, fieldName)) {
                    try {
                        store._.sortRecordList(record._proxy[fieldName]._proxy, func);
                    } catch (err) {
                        store.handleError(err);
                    }
                } else {
                    // sort on copy of list so that reactive observers not triggered while sorting
                    const copy = [...record._proxy[fieldName]];
                    copy.sort(func);
                    const hasChanged = copy.some(
                        (item, index) => item !== record[fieldName][index]
                    );
                    if (hasChanged) {
                        record._proxy[fieldName] = copy;
                    }
                }
                this.fieldsSorting.delete(fieldName);
            })
        );
        this.fieldsSortStop.set(fieldName, stopFn);
        record._registerDisposeFn(stopFn);
        if (fromInNeed) {
            this.fieldsSortInNeed.set(fieldName, true);
        }
        triggered = true;
    }
    onUpdate(record, fieldName) {
        const store = record._rawStore;
        const Model = record.Model;
        if (!Model._.fieldsOnUpdate.get(fieldName)) {
            return;
        }
        this.fieldsOnUpdateStop.get(fieldName)?.();
        const recordProxy = record._proxy;
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
        this.prepareFieldOnUpdate(record, fieldName, recordProxy);
    }
}
