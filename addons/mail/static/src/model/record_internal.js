/** @typedef {import("./record_list").RecordList} RecordList */

import {
    IS_RECORD_SYM,
    STORE_SYM,
    fields,
    isComputedDefinition,
    isFieldDefinition,
    isMany,
    isRelation,
    technicalKeysOnRecords,
    untrackFunctions,
} from "./misc";
import { RecordList } from "./record_list";
import { Scope, computed, markRaw, proxy, signal, untrack } from "@odoo/owl";
import { computedUntilStale } from "@mail/utils/common/signal";
import { RecordUses } from "./record_uses";

/**
 * Owner of the owl computeds of one record. owl attaches a computed to the
 * scope that is active when it is created and disposes it with that scope, so
 * without a scope of its own a record loses its computeds as soon as the
 * component that happened to create them is destroyed.
 */
class RecordScope extends Scope {
    /** @param {Record} record */
    constructor(record) {
        super(record.store._.app);
        this.record = record;
        record._registerDisposeFn(() => this.destroy());
    }

    destroy() {
        this.finalize((error) => this.record.store.handleError(error));
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
     * All dispose functions for this record.
     * For the store, this stores the dispose functions of all records.
     * Useful to automatically call the dispose functions when the record is deleted or in-between each tests.
     *
     * @type {Set<Function>}
     */
    disposeFns = new Set();
    /**
     *
     * @type {Map<string, () => any>}
     */
    computedGetters = new Map();
    /**
     *
     * @type {import("@odoo/owl").Signal<boolean>}
     */
    isConstructing = signal(true);
    /**
     *
     * @type {Set<string>}
     */
    fieldsDeclared = new Set();
    uses = new RecordUses();
    /**
     *
     * @type {Map<string, import("./record_list").RecordList>}
     */
    fieldsList = new Map();
    /**
     *
     * @type {Map<string, import("@odoo/owl").Signal>}
     */
    fieldsSignal = new Map();
    /**
     *
     * @type {import("@odoo/owl").Signal<boolean>}
     */
    existsSignal = signal(true);
    /**
     *
     * @type {import("@odoo/owl").Signal<boolean>}
     */
    deletingSignal = signal(false);
    /**
     *
     * @type {RecordScope}
     */
    scope;
    /** @type {string} */
    localId;
    /**
     *
     * @type {Map<string|symbol, { fn: Function, bound: Function }>}
     */
    boundFns = new Map();
    /** @type {Map<string, import("@mail/model/field_version").SingleFieldVersion|import("@mail/model/field_version").ManyFieldVersion>} */
    fieldsVersion = new Map();

    /**
     *
     * @param {Record} record
     * @param {string} name
     * @returns {any}
     */
    /**
     * @param {Record} record
     * @returns {RecordScope} the scope owning the computeds of this record
     */
    ensureScope(record) {
        return (this.scope ??= new RecordScope(record));
    }

    constructor() {
        markRaw(this);
    }

    /**
     * The value declared with `record.computed()`: computed on the
     * first read, then kept in an owl computed of its own. The declaration sits
     * on the record until that read, which is where its compute and its initial
     * value come from.
     *
     * @param {Record} record
     * @param {Record} rawRecord
     * @param {string} name
     */
    computedField(record, rawRecord, name) {
        let computedGetter = this.computedGetters.get(name);
        if (computedGetter) {
            return computedGetter();
        }
        const self = this;
        const Model = record.Model;
        const storeInternal = Model.store._;
        const { compute, msUntilStale } = rawRecord[name];
        delete rawRecord[name];
        let lastValue;
        function computedGetterReader() {
            if (!self.existsSignal() || self.deletingSignal()) {
                return lastValue;
            }
            if (untrack(() => storeInternal.deletingRecords())) {
                void storeInternal.deletingRecords();
                return lastValue;
            }
            lastValue = compute.call(record);
            return lastValue;
        }
        computedGetter = this.ensureScope(record).run(() =>
            msUntilStale
                ? computedUntilStale(computedGetterReader, msUntilStale)
                : computed(computedGetterReader)
        );
        this.computedGetters.set(name, computedGetter);
        return computedGetter();
    }

    /**
     *
     * @param {Record} rawRecord
     * @returns {Record}
     */
    setupRecord(rawRecord) {
        const self = this;
        const Model = rawRecord.Model;
        const record = new Proxy(rawRecord, {
            get(...args) {
                return self.proxyGet(...args);
            },
            defineProperty(target, name, descriptor) {
                if (descriptor.enumerable && descriptor.writable && "value" in descriptor) {
                    return self.proxySet(target, name, descriptor.value, record);
                }
                return Reflect.defineProperty(target, name, descriptor);
            },
            deleteProperty(target, name) {
                return self.proxyDeleteProperty(target, name, record);
            },
            set(...args) {
                return self.proxySet(...args);
            },
        });
        markRaw(record); // record reactivity is done through field signals
        if (rawRecord[STORE_SYM]) {
            rawRecord.env = Model.store.env;
            /** @type {Map<string, Record>} */
            rawRecord.recordByLocalId = Model.store.recordByLocalId;
            rawRecord.Models = Model.store.Models;
            Object.assign(rawRecord, Model.store.Models);
        }
        return record;
    }

    /**
     * @param {Record} record
     * @param {string} name
     * @returns {RecordList}
     */
    ensureRecordList(record, name) {
        let recordList = this.fieldsList.get(name);
        if (!recordList) {
            recordList = new RecordList(0, record, name);
            this.fieldsList.set(name, recordList);
        }
        return recordList;
    }

    /**
     * Get-or-create the signal containing the value of the attr field `name`
     * (declared or dynamic), its sole storage, and return it. `definition`
     * is a field definition (a declaration write intercepted by proxySet,
     * carrying the per-record default) or a plain initial value. Idempotent;
     * a declaration's default
     * never overrides an updated value, and a default is not an update (the
     * signal is written directly, without the update machinery).
     *
     * @param {string} name
     * @param {any} [definition] field definition or plain initial value
     * @returns {import("@odoo/owl").Signal}
     */
    ensureFieldSignal(name, definition) {
        let sig = this.fieldsSignal.get(name);
        if (sig && definition === undefined) {
            return sig; // fast path: prepared attr, plain access
        }
        const defaultValue = isFieldDefinition(definition) ? definition.default : definition;
        if (!sig) {
            sig = signal(defaultValue);
            this.fieldsSignal.set(name, sig);
        } else if (isFieldDefinition(definition)) {
            if (sig() === undefined) {
                sig.set(defaultValue);
            }
        }
        return sig;
    }

    /**
     * @param {Record} rawRecord
     * @param {string} name
     * @param {Record} record forwarded by the constructor trap
     */
    proxyDeleteProperty(rawRecord, name, record) {
        const self = this;
        const Model = rawRecord.Model;
        const parentFieldName = Model._.resolveParentField(name);
        if (parentFieldName) {
            const parentRecord = record[parentFieldName];
            return Reflect.deleteProperty(parentRecord, name);
        }
        return Model.store.MAKE_UPDATE(function recordDeleteProperty() {
            if (isRelation(Model, name)) {
                self.ensureRecordList(record, name).clear();
                return true;
            }
            self.ensureFieldSignal(name).set(undefined);
            return true;
        });
    }

    /**
     * @param {Record} rawRecord
     * @param {string} name
     * @param {Record} record the receiver: the record itself
     */
    proxyGet(rawRecord, name, record) {
        if (name === "_") {
            return this;
        }
        if (typeof name === "symbol") {
            const sig = this.fieldsSignal.get(name);
            if (sig) {
                return sig();
            }
            return Reflect.get(...arguments);
        }
        if (technicalKeysOnRecords.has(name)) {
            return Reflect.get(...arguments);
        }
        const sig = this.fieldsSignal.get(name);
        if (sig !== undefined) {
            const val = sig();
            if (rawRecord.Model._.fieldsAttrAsProxy.has(name)) {
                return proxy(val);
            }
            return val;
        }
        const recordList = this.fieldsList.get(name);
        if (recordList !== undefined) {
            if (rawRecord.Model._.fieldsMany.get(name)) {
                return recordList;
            }
            return recordList[0];
        }
        const Model = rawRecord.Model;
        if (Model._.fieldsComputable.has(name)) {
            return this.computedField(record, rawRecord, name);
        }
        const parentFieldName = Model._.resolveParentField(name);
        if (parentFieldName) {
            const parentRecord = record[parentFieldName];
            if (!parentRecord) {
                const ParentModel = Model.store[Model._.fieldsTargetModel.get(parentFieldName)];
                if (isMany(ParentModel, name)) {
                    return [];
                }
                return;
            }
            return Reflect.get(parentRecord, name);
        }
        if (!Model._.fields.get(name)) {
            const res = Reflect.get(...arguments);
            if (typeof res === "function" && !res._) {
                const memo = this.boundFns.get(name);
                if (memo?.fn === res) {
                    return memo.bound;
                }
                const bound = res.bind(record);
                this.boundFns.set(name, { fn: res, bound });
                return bound;
            }
            return res;
        }
        if (isRelation(Model, name)) {
            const recordList = this.ensureRecordList(record, name);
            if (isMany(Model, name)) {
                return recordList;
            }
            return recordList[0];
        }
        const val = this.ensureFieldSignal(name)();
        if (Model._.fieldsAttrAsProxy.has(name)) {
            return proxy(val);
        }
        return val;
    }

    /**
     * @param {Record} rawRecord
     * @param {string} name
     * @param {any} val
     * @param {Record} record the receiver, or forwarded by the defineProperty
     *   constructor trap (which has no native receiver)
     */
    proxySet(rawRecord, name, val, record) {
        const Model = rawRecord.Model;
        const store = rawRecord.store;
        if (isComputedDefinition(val)) {
            if (isComputedDefinition(rawRecord[name])) {
                throw new Error(
                    `${Model.getName()}.${name}: a computed cannot be redeclared, patch the method its compute calls`
                );
            }
            // the declaration stays on the record, proxyGet takes it on the first
            // read: define it, as the name may already carry a field accessor
            Model._.fieldsComputable.add(name);
            return Reflect.defineProperty(rawRecord, name, {
                configurable: true,
                enumerable: true,
                value: val,
                writable: true,
            });
        }
        if (isFieldDefinition(val)) {
            if (this.fieldsDeclared.has(name)) {
                console.warn(
                    `Field "${name}" on model "${Model.getName()}" is already defined; the redefinition is ignored.`
                );
                return true;
            }
            this.fieldsDeclared.add(name);
            if (!Model._.fields.get(name)) {
                Model._.registerField(name, val);
            }
            if (isRelation(Model, name)) {
                this.ensureRecordList(record, name);
            } else {
                this.ensureFieldSignal(name, val);
            }
            return true;
        }
        if (!this.isConstructing()) {
            const parentFieldName = Model._.resolveParentField(name);
            if (parentFieldName) {
                const parentRecord = record[parentFieldName];
                return Reflect.set(parentRecord, name, val);
            }
        }
        if (
            this.isConstructing() &&
            typeof name === "string" &&
            !Model._.fields.get(name) &&
            !technicalKeysOnRecords.has(name)
        ) {
            Model._.registerField(name, fields.Attr(val));
            this.ensureFieldSignal(name, val);
            return true;
        }
        if (Model._.fields.get(name) && !isRelation(Model, name) && !this.fieldsSignal.has(name)) {
            this.ensureFieldSignal(name, val);
            return true;
        }
        if (
            typeof name === "string" &&
            !Model._.fields.get(name) &&
            !Model._.fieldsComputable.has(name) &&
            !technicalKeysOnRecords.has(name)
        ) {
            for (
                let proto = Object.getPrototypeOf(rawRecord);
                proto && proto !== Object.prototype;
                proto = Object.getPrototypeOf(proto)
            ) {
                const descriptor = Object.getOwnPropertyDescriptor(proto, name);
                if (descriptor) {
                    if (descriptor.set) {
                        return Reflect.set(proto, name, val, record);
                    }
                    break;
                }
            }
            console.warn(
                `Dropping unknown field "${name}" written on "${Model.getName()}": records only hold declared fields.`
            );
            return true;
        }
        if (isRelation(Model, name)) {
            this.ensureRecordList(record, name);
        }
        return store.MAKE_UPDATE(function recordSet() {
            store._.updateFields(record, { [name]: val });
            return true;
        });
    }
}

untrackFunctions(RecordInternal.prototype, [
    "ensureFieldSignal",
    "ensureRecordList",
    "proxyDeleteProperty",
    "proxySet",
]);
