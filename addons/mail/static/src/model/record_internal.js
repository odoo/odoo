/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

import {
    IS_DELETED_SYM,
    IS_RECORD_SYM,
    isFieldDefinition,
    isMany,
    isRelation,
    makeRecordFieldLocalId,
    untrackFunctions,
} from "./misc";
import { RecordList } from "./record_list";
import {
    Scope,
    computed,
    immediateEffect,
    markRaw,
    proxy,
    signal,
    toRaw,
    untrack,
} from "@odoo/owl";
import { RecordUses } from "./record_uses";
import { LocalStorageEntry } from "@mail/utils/common/local_storage";

/**
 * Observe one field of a record, without running the callback on the initial
 * read. Only the lazy compute flags need this: they watch a single
 * field name resolved at runtime, while `Record.onChange` takes the reads to
 * observe as a function.
 *
 * @param {Record} recordProxy
 * @param {string} fieldName
 * @param {Function} callback
 * @returns {Function} dispose function
 */
function observeField(recordProxy, fieldName, callback) {
    let running = false;
    const targetProxy = proxy(recordProxy);
    const disposeFn = untrack(() =>
        immediateEffect(() => {
            // read once: a reactive get() per read would be observed as many times
            const val = targetProxy[fieldName];
            if (typeof val === "object" && val !== null) {
                void Object.keys(val);
            }
            if (Array.isArray(val)) {
                void val.length;
                void val.forEach((i) => i);
            }
            if (running) {
                untrack(() => callback());
            }
        })
    );
    running = true;
    return disposeFn;
}

/**
 * Owner of the owl computeds of one record. owl attaches a computed to the
 * scope that is active when it is created and disposes it with that scope, so
 * without a scope of its own a record loses its computeds as soon as the
 * component that happened to create them is destroyed.
 */
class RecordScope extends Scope {
    /** @param {import("models").Store} store */
    constructor(store) {
        super(store._.app);
        this.store = store;
    }

    destroy() {
        this.finalize((error) => this.store.handleError(error));
    }

    /**
     * A deleted record can still be read, and owl refuses to run in a
     * destroyed scope: ignore this scope then, and let the calling one own the
     * computeds.
     *
     * @param {Function} fn returning a promise here ties it to the record: owl
     *  rejects it with an AbortError once the record is deleted
     */
    run(fn, ...args) {
        return this.isDestroyed() ? fn(...args) : super.run(fn, ...args);
    }
}

export class RecordInternal {
    [IS_RECORD_SYM] = true;
    /**
     * Whether the record is being created: set until Record.new assigned the
     * ids and registered the record. A signal, so that clearing it re-runs the
     * onChange registrations held during setup().
     *
     * @type {import("@odoo/owl").Signal<boolean>}
     */
    isConstructing = signal(true);
    /**
     * All dispose functions for this record.
     * For the store, this stores the dispose functions of all records.
     * Useful to automatically call the dispose functions when the record is deleted or in-between each tests.
     *
     * @type {Set<Function>}
     */
    disposeFns = new Set();
    /**
     * Scope holding the owl computeds of this record, made on the first one and
     * disposed with the record.
     *
     * @type {RecordScope}
     */
    scope;
    // Note: state of fields in Maps rather than object is intentional for improved performance.
    /**
     * For computed field, determines whether the field is computing its value.
     *
     * @type {Map<string, boolean>}
     */
    fieldsComputing = new Map();
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
     * Value of a field kept in a per-record owl computed(): computed on the
     * first read and cached until one of the values it reads changes, instead
     * of being scheduled and stored by the model. Key is fieldName.
     *
     * @type {Map<string, () => any>}
     */
    fieldsComputed = new Map();
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

    constructor() {
        markRaw(this);
    }

    /**
     * @param {Record} record
     * @returns {RecordScope} the scope owning the computeds of this record
     */
    ensureScope(record) {
        return (this.scope ??= new RecordScope(record._rawStore));
    }

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
            if (!Model._.fieldsEager.get(fieldName) && !Model._.fieldsComputable.get(fieldName)) {
                record._registerDisposeFn(
                    observeField(recordProxy, fieldName, () => {
                        if (this.fieldsComputing.get(fieldName)) {
                            /**
                             * Use a reactive to reset the computeInNeed flag when there is
                             * a change. This assumes when other reactive are still
                             * observing the value, its own callback will reset the flag to
                             * true through the proxy getters.
                             */
                            this.fieldsComputeInNeed.delete(fieldName);
                        }
                    })
                );
                // reset flags triggered by registering onChange
                this.fieldsComputeInNeed.delete(fieldName);
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

    /**
     * @param {Record} record
     * @param {string} name
     */
    proxyDeleteProperty(record, name) {
        const Model = record.Model;
        if (Model._.parentFields.has(name)) {
            const parentFieldName = Model._.parentFields.get(name);
            const parentRecordProxyInternal = record._proxyInternal[parentFieldName];
            return Reflect.deleteProperty(parentRecordProxyInternal, name);
        }
        return Model._rawStore.MAKE_UPDATE(function recordDeleteProperty() {
            if (isRelation(Model, name)) {
                const recordList = record[name];
                recordList.clear();
                return true;
            }
            return Reflect.deleteProperty(record, name);
        });
    }

    /**
     * @param {Record} record
     * @param {string} name
     * @param {Record} recordFullProxy
     */
    proxyGet(record, name, recordFullProxy) {
        const Model = record.Model;
        const Models = record._rawStore.Models;
        if (Model._.parentFields.has(name)) {
            const parentFieldName = Model._.parentFields.get(name);
            const parentRecordFullProxy = recordFullProxy[parentFieldName];
            if (!parentRecordFullProxy) {
                const ParentModel = Models[Model._.fieldsTargetModel.get(parentFieldName)];
                if (isMany(ParentModel, name)) {
                    return [];
                }
                return;
            }
            return Reflect.get(parentRecordFullProxy, name);
        }
        if (record._.gettingField || !Model._.fields.get(name)) {
            let res = Reflect.get(...arguments);
            // a model is a class, so a function: binding it would hide its statics
            if (typeof res === "function" && !res._) {
                res = res.bind(recordFullProxy);
            }
            return res;
        }
        if (Model._.fieldsComputable.get(name)) {
            let computedField = record._.fieldsComputed.get(name);
            if (!computedField) {
                const compute = Model._.fieldsCompute.get(name);
                const { isUpdateInProgress } = record._rawStore._;
                let lastValue = record._.fieldsDefault.get(name);
                computedField = record._.ensureScope(record).run(() =>
                    computed(function computeFieldValue() {
                        if (untrack(isUpdateInProgress)) {
                            // Hold while a write is being applied: the relations this
                            // reads are written one by one. onAdd, onDelete and onUpdate
                            // run between writes, at depth 0, so they read fresh values.
                            // Subscribe only while held, so the release computes once.
                            void isUpdateInProgress();
                            return lastValue;
                        }
                        lastValue = compute.call(record._proxy);
                        return lastValue;
                    })
                );
                record._.fieldsComputed.set(name, computedField);
            }
            return computedField();
        }
        if (Model._.fieldsCompute.get(name) && !Model._.fieldsEager.get(name)) {
            record._.fieldsComputeInNeed.set(name, true);
            if (record._.fieldsComputeOnNeed.get(name)) {
                record._.compute(record, name, { fromInNeed: true });
            }
        }
        record._.gettingField = true;
        let val;
        try {
            val = recordFullProxy[name];
        } finally {
            record._.gettingField = false;
        }
        if (isRelation(Model, name)) {
            const recordListFullProxy = val._proxy;
            if (isMany(Model, name)) {
                return recordListFullProxy;
            }
            return recordListFullProxy[0];
        }
        return Reflect.get(record, name, recordFullProxy);
    }

    /**
     * @param {Record} record
     * @param {string} name
     * @param {any} val
     * @param {any} receiver
     */
    proxySet(record, name, val, receiver) {
        const Model = record.Model;
        const store = record._rawStore;
        if (Model._.parentFields.has(name)) {
            const parentFieldName = Model._.parentFields.get(name);
            const parentRecordProxyInternal = record._proxyInternal[parentFieldName];
            return Reflect.set(parentRecordProxyInternal, name, val);
        }
        // ensure each field write goes through the updatingAttrs method exactly once
        if (record._.updatingAttrs.has(name)) {
            record[name] = val;
            return true;
        }
        return store.MAKE_UPDATE(function recordSet() {
            const reactiveSet = receiver !== record._proxyInternal;
            if (reactiveSet) {
                record._.proxyUsed.set(name, true);
            }
            store._.updateFields(record, { [name]: val });
            if (reactiveSet) {
                record._.proxyUsed.delete(name);
            }
            return true;
        });
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

untrackFunctions(RecordInternal.prototype, ["proxyDeleteProperty", "proxySet"]);
