/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

import {
    IS_RECORD_SYM,
    isComputedDefinition,
    isFieldDefinition,
    isMany,
    isRelation,
    makeRecordFieldLocalId,
    technicalKeysOnRecords,
    untrackFunctions,
} from "./misc";
import { computedUntilStale } from "@mail/utils/common/signal";
import { RecordList } from "./record_list";
import { Scope, computed, immediateEffect, markRaw, proxy, signal, untrack } from "@odoo/owl";
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
    const disposeFn = untrack(() =>
        immediateEffect(() => {
            // read once: a reactive get() per read would be observed as many times
            const val = recordProxy[fieldName];
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
    /** @param {Record} record */
    constructor(record) {
        super(record._rawStore._.app);
        this.record = record;
        record._registerDisposeFn(() => this.destroy());
    }

    destroy() {
        this.finalize((error) => this.record._rawStore.handleError(error));
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
     * Values declared with `computed()`. Key is the name, Value is the
     * getter of the owl computed made on the first read, which caches until
     * something it read changes.
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
    /**
     * Value of each attr field of this record, declared or not, one signal per
     * field: the sole storage, and the only thing a read of that field observes.
     *
     * @type {Map<string, import("@odoo/owl").Signal<any>>}
     */
    fieldsAttrSignal = new Map();
    /**
     * Whether the record is deleted. A signal, so that setting it re-runs the
     * readers of `exists()`.
     *
     * @type {import("@odoo/owl").Signal<boolean>}
     */
    isDeleted = signal(false);
    uses = new RecordUses();
    /** @type {string} */
    localId;
    /** @type {Record} the record these internals belong to */
    record;
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
     * Get-or-create the signal holding the value of the attr field `fieldName`,
     * declared or not.
     *
     * @param {string} fieldName
     * @param {any} [value] initial value, on creation only
     * @param {Object} [param2={}]
     * @param {boolean} [param2.accessor=true] whether to define the accessor
     *  that reads and writes the field as a property of the record
     * @returns {import("@odoo/owl").Signal<any>}
     */
    ensureFieldSignal(fieldName, value, { accessor = true } = {}) {
        let sig = this.fieldsAttrSignal.get(fieldName);
        if (sig) {
            return sig;
        }
        sig = signal(value);
        this.fieldsAttrSignal.set(fieldName, sig);
        if (accessor) {
            Object.defineProperty(this.record, fieldName, {
                configurable: true,
                enumerable: true,
                get: () => sig(),
                set: (val) => {
                    sig.set(val);
                },
            });
        }
        return sig;
    }

    /** @returns {RecordScope} the scope owning the computeds of this record */
    ensureScope() {
        return (this.scope ??= new RecordScope(this.record));
    }

    /**
     * @param {() => any} compute
     * @param {(value: any) => number|void} [msUntilStale]
     * @returns {() => any} the computed holding the value
     */
    makeComputed(compute, msUntilStale) {
        const record = this.record;
        // the last computed value, answered while a write is being applied
        let heldValue;
        const { isUpdateInProgress } = record._rawStore._;
        const { isDeleted } = this;
        function computeValue() {
            if (isDeleted()) {
                return heldValue;
            }
            if (untrack(isUpdateInProgress)) {
                // Hold while a write is being applied: the relations this
                // reads are written one by one. onAdd, onDelete and onUpdate
                // run between writes, at depth 0, so they read fresh values.
                // Subscribe only while held, so the release computes once.
                void isUpdateInProgress();
                return heldValue;
            }
            heldValue = compute.call(record._proxy);
            return heldValue;
        }
        return this.ensureScope().run(() =>
            msUntilStale ? computedUntilStale(computeValue, msUntilStale) : computed(computeValue)
        );
    }

    /**
     * @param {Record} record
     * @param {Object} [ids] the identifying values, from `Record.new`
     * @returns {Record} the proxy of the record, which its constructor returns
     */
    prepareRecord(record, ids) {
        this.record = record;
        this.localId = record.Model.localId(ids);
        record._proxy = markRaw(
            new Proxy(record, {
                defineProperty: (target, name, descriptor) =>
                    this.proxyDefineProperty(name, descriptor),
                deleteProperty: (target, name) => this.proxyDeleteProperty(name),
                get: (target, name) => this.proxyGet(name),
                set: (target, name, value) => this.proxySet(name, value),
            })
        );
        return record._proxy;
    }

    /**
     * @param {string} fieldName
     * @returns {boolean} whether the field holds its value on this record
     */
    fieldPrepared(fieldName) {
        const record = this.record;
        if (isRelation(record.Model, fieldName)) {
            return record[fieldName] !== undefined;
        }
        return this.fieldsAttrSignal.has(fieldName);
    }

    /**
     * @param {string} fieldName
     * @param {any} definition the field definition, or the default value
     */
    prepareField(fieldName, definition) {
        const record = this.record;
        const Model = record.Model;
        if (isRelation(Model, fieldName)) {
            const recordList = new RecordList();
            Object.assign(recordList._, {
                name: fieldName,
                owner: record,
            });
            record[fieldName] = recordList;
        } else {
            const value = isFieldDefinition(definition) ? definition.default : definition;
            this.ensureFieldSignal(fieldName, value);
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
                record._registerDisposeFn(
                    observeField(record._proxy, fieldName, () => {
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
            this.prepareFieldOnUpdate(fieldName);
        }
    }

    /** @param {string} fieldName */
    prepareFieldOnUpdate(fieldName) {
        const record = this.record;
        const Model = record.Model;
        const store = Model.store;
        const fn = store._onChange(record._proxy, fieldName, (obs) => {
            if (store._.UPDATE !== 0) {
                untrack(() => store._.ADD_QUEUE("onUpdate", record, fieldName));
            } else {
                this.onUpdate(fieldName);
            }
        });
        this.fieldsOnUpdateStop.set(fieldName, fn);
    }

    /** @param {string} name */
    proxyDeleteProperty(name) {
        const record = this.record;
        const Model = record.Model;
        if (Model._.parentFields.has(name)) {
            const parentFieldName = Model._.parentFields.get(name);
            const parentRecordProxy = record._proxy[parentFieldName];
            return Reflect.deleteProperty(parentRecordProxy, name);
        }
        return Model._rawStore.MAKE_UPDATE(function recordDeleteProperty() {
            if (isRelation(Model, name)) {
                const recordList = record[name];
                recordList.clear();
                return true;
            }
            record._.ensureFieldSignal(name).set(undefined);
            return true;
        });
    }

    /** @param {string} name */
    proxyGet(name) {
        const record = this.record;
        const recordProxy = record._proxy;
        if (technicalKeysOnRecords.has(name)) {
            return record[name];
        }
        const Model = record.Model;
        const modelInternal = Model._;
        if (modelInternal.parentFields.has(name)) {
            const parentFieldName = modelInternal.parentFields.get(name);
            const parentRecordProxy = recordProxy[parentFieldName];
            if (!parentRecordProxy) {
                const Models = record._rawStore.Models;
                const ParentModel = Models[modelInternal.fieldsTargetModel.get(parentFieldName)];
                if (isMany(ParentModel, name)) {
                    return [];
                }
                return;
            }
            return Reflect.get(parentRecordProxy, name);
        }
        if (modelInternal.fields.get(name)) {
            if (modelInternal.fieldsCompute.get(name) && !modelInternal.fieldsEager.get(name)) {
                record._.fieldsComputeInNeed.set(name, true);
                if (record._.fieldsComputeOnNeed.get(name)) {
                    record._.compute(name, { fromInNeed: true });
                }
            }
            const sig = record._.fieldsAttrSignal.get(name);
            if (sig) {
                const val = sig();
                if (
                    typeof val === "object" &&
                    val !== null &&
                    modelInternal.fieldsAttrAsProxy.has(name)
                ) {
                    // Return the value as a proxy, as this field is mutated in place.
                    return proxy(val);
                }
                return val;
            }
            if (isRelation(Model, name)) {
                const recordList = record[name];
                if (recordList !== undefined) {
                    const recordListProxy = recordList._proxy;
                    if (isMany(Model, name)) {
                        return recordListProxy;
                    }
                    return recordListProxy[0];
                }
            }
            // a field this record does not hold yet: `setup` reads the
            // prototype before writing such a field
        }
        const sig = record._.fieldsAttrSignal.get(name);
        if (sig) {
            return sig();
        }
        if (modelInternal.fieldsComputable.has(name)) {
            let computedGetter = this.fieldsComputed.get(name);
            if (!computedGetter) {
                // the declaration sits on the record until its first read
                const { compute, msUntilStale } = record[name];
                delete record[name];
                computedGetter = this.makeComputed(compute, msUntilStale);
                this.fieldsComputed.set(name, computedGetter);
            }
            return computedGetter();
        }
        let res = Reflect.get(record, name, recordProxy);
        if (
            res === undefined &&
            typeof name === "string" &&
            !technicalKeysOnRecords.has(name) &&
            !(name in record)
        ) {
            // Create the signal on read, so a reader before the first write observes it.
            return record._.ensureFieldSignal(name, undefined, {
                accessor: false,
            })();
        }
        // a model is a class, so a function: binding it would hide its statics
        if (typeof res === "function" && !res._) {
            res = res.bind(recordProxy);
        }
        return res;
    }

    /**
     * @param {Record} record
     * @param {string} name
     * @param {any} val
     */
    /**
     * Route a plain data descriptor through the set trap, as patching a
     * record defines the field rather than sets it.
     */
    proxyDefineProperty(name, descriptor) {
        const record = this.record;
        if (typeof name === "symbol") {
            return Reflect.defineProperty(record, name, descriptor);
        }
        if (technicalKeysOnRecords.has(name)) {
            // keep what the constructor set: `Store` redeclares `_` for typing
            return true;
        }
        if (!descriptor.enumerable || !descriptor.writable || !("value" in descriptor)) {
            return Reflect.defineProperty(record, name, descriptor);
        }
        return this.proxySet(name, descriptor.value);
    }

    proxySet(name, val) {
        const record = this.record;
        const Model = record.Model;
        if (isComputedDefinition(val)) {
            // the declaration sits on the record until its first read
            return Reflect.set(record, name, val);
        }
        if (isFieldDefinition(val) || (Model._.fields.get(name) && !this.fieldPrepared(name))) {
            // a declaration: an initializer lands the definition or the default,
            // and `setup` writes the default of a field no initializer declares
            this.prepareField(name, val);
            return true;
        }
        const store = record._rawStore;
        if (Model._.parentFields.has(name)) {
            const parentFieldName = Model._.parentFields.get(name);
            const parentRecordProxy = record._proxy[parentFieldName];
            return Reflect.set(parentRecordProxy, name, val);
        }
        return store.MAKE_UPDATE(function recordSet() {
            store._.updateFields(record, { [name]: val });
            return true;
        });
    }

    requestCompute(fieldName, { force = false } = {}) {
        if (untrack(this.isDeleted)) {
            return;
        }
        const record = this.record;
        const Model = record.Model;
        if (!Model._.fieldsCompute.get(fieldName)) {
            return;
        }
        const store = record._rawStore;
        if (store._.UPDATE !== 0 && !force) {
            store._.ADD_QUEUE("compute", record, fieldName);
        } else {
            if (Model._.fieldsEager.get(fieldName) || this.fieldsComputeInNeed.get(fieldName)) {
                this.compute(fieldName);
            } else {
                this.fieldsComputeOnNeed.set(fieldName, true);
            }
        }
    }
    /**
     * @param {string} fieldName
     * @param {Object} [param1={}]
     * @param {boolean} [param1.fromInNeed] whether the compute is triggered from an "in-need" observer.
     *  Useful to force keeping the "in-need" flag, as the "in-need" is automatically reset whenever a computing value has changed.
     *  The "in-need" flag is expected to be set again by observed on the next read, but if the compute is immediately triggered
     *  by the "in-need" then that's the case the `fromInNeed: true` and it should preserve for this ongoing compute.
     */
    compute(fieldName, { fromInNeed } = {}) {
        const record = this.record;
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
                    return untrack(() => this.requestCompute(fieldName));
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
    onUpdate(fieldName) {
        const record = this.record;
        const store = record._rawStore;
        const Model = record.Model;
        if (!Model._.fieldsOnUpdate.get(fieldName)) {
            return;
        }
        this.fieldsOnUpdateStop.get(fieldName)?.();
        const recordProxy = record._proxy;
        untrack(() => {
            try {
                Model._.fieldsOnUpdate
                    .get(fieldName)
                    .forEach((fn) => fn.call(recordProxy, recordProxy[fieldName]));
            } catch (err) {
                store.handleError(err);
            }
        });
        this.prepareFieldOnUpdate(fieldName);
    }
}

untrackFunctions(RecordInternal.prototype, ["proxyDeleteProperty", "proxySet"]);
