/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

import {
    IS_RECORD_SYM,
    isComputedDefinition,
    isFieldDefinition,
    isMany,
    isRelation,
    technicalKeysOnRecords,
    untrackFunctions,
} from "./misc";
import { computedUntilStale } from "@mail/utils/common/signal";
import { RecordList } from "./record_list";
import { Scope, computed, markRaw, proxy, signal, untrack } from "@odoo/owl";
import { RecordUses } from "./record_uses";

/**
 * The owl scope of one record, owner of its computeds and of its effects.
 *
 * Without a scope of its own, a record loses its computeds as soon as the
 * component that happened to create them is destroyed, as owl attaches a
 * computed to the scope active when the computed is made. An effect has no
 * such link at all, so it registers its stop function here.
 */
class RecordScope extends Scope {
    /** @param {Record} record */
    constructor(record) {
        super(record._rawStore._.app);
        this.record = record;
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
     * Scope holding the owl computeds and the effects of this record, made on
     * the first one and disposed with the record.
     *
     * @type {RecordScope}
     */
    scope;
    // Note: state of fields in Maps rather than object is intentional for improved performance.
    /**
     * Values declared with `computed()`. Key is the name, Value is the
     * getter of the owl computed made on the first read, which caches until
     * something it read changes.
     *
     * @type {Map<string, () => any>}
     */
    fieldsComputed = new Map();
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
     * @param {(a: any, b: any) => boolean} [equals]
     * @returns {() => any} the computed holding the value
     */
    makeComputed(compute, msUntilStale, equals) {
        const record = this.record;
        // the last computed value, answered while a write is being applied
        // (except for the writes of the queues drain, see `MAKE_UPDATE`)
        let heldValue;
        let hasValue = false;
        const { isUpdateInProgress } = record._rawStore._;
        const { isDeleted } = this;
        function computeValue() {
            if (isDeleted()) {
                return heldValue;
            }
            if (hasValue && untrack(isUpdateInProgress)) {
                // Hold while a write is being applied: the relations this
                // reads are written one by one. An immediate onChange runs
                // between writes, at depth 0, so it reads fresh values.
                // Subscribe only while held, so the release computes once.
                void isUpdateInProgress();
                return heldValue;
            }
            heldValue = compute.call(record._proxy);
            hasValue = true;
            return heldValue;
        }
        return this.ensureScope().run(() =>
            msUntilStale
                ? computedUntilStale(computeValue, msUntilStale, { equals })
                : computed(computeValue, { equals })
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
                const { compute, msUntilStale, equals } = record[name];
                delete record[name];
                computedGetter = this.makeComputed(compute, msUntilStale, equals);
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
}

untrackFunctions(RecordInternal.prototype, ["proxyDeleteProperty", "proxySet"]);
