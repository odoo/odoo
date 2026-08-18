/** @typedef {import("./record").Record} Record */
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
    versionKeys,
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
        super(record.store._.app);
        this.record = record;
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
     * Value of each attr field of this record, one signal per field: the sole
     * storage, and the only thing a read of that field observes.
     *
     * @type {Map<string, import("@odoo/owl").Signal<any>>}
     */
    fieldsAttrSignal = new Map();
    /** @type {Map<string, import("./record_list").RecordList>} */
    fieldsList = new Map();
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
    /** @type {Set<string>|undefined} */
    fieldsDeclared = new Set();
    /** @type {Map<string, import("@mail/model/field_version").SingleFieldVersion|import("@mail/model/field_version").ManyFieldVersion>} */
    fieldsVersion = new Map();

    constructor() {
        markRaw(this);
    }

    /**
     * Get-or-create the signal holding the value of the attr field `name`.
     *
     * @param {string} name
     * @param {any} [definition] field definition or plain initial value
     * @returns {import("@odoo/owl").Signal}
     */
    ensureFieldSignal(name, definition) {
        let sig = this.fieldsAttrSignal.get(name);
        if (sig && definition === undefined) {
            return sig;
        }
        const defaultValue = isFieldDefinition(definition) ? definition.default : definition;
        if (!sig) {
            sig = signal(defaultValue);
            this.fieldsAttrSignal.set(name, sig);
        } else if (isFieldDefinition(definition)) {
            if (sig() === undefined) {
                sig.set(defaultValue);
            }
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
        // (except for the writes of a record deletion, see `MAKE_UPDATE`)
        let heldValue;
        let hasValue = false;
        const { isUpdateInProgress } = record.store._;
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
            heldValue = compute.call(record);
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
     * @param {Record} rawRecord
     * @param {Object} [ids] the identifying values, from `Record.new`
     * @returns {Record} the proxy of the record, which its constructor returns
     */
    prepareRecord(rawRecord, ids) {
        this.localId = rawRecord.Model.localId(ids);
        this.record = markRaw(
            new Proxy(rawRecord, {
                defineProperty: (target, name, descriptor) =>
                    this.proxyDefineProperty(target, name, descriptor),
                deleteProperty: (target, name) => this.proxyDeleteProperty(target, name),
                get: (target, name) => this.proxyGet(target, name),
                set: (target, name, value) => this.proxySet(target, name, value),
            })
        );
        if (rawRecord[STORE_SYM]) {
            const store = rawRecord.Model.store;
            rawRecord.env = store.env;
            Object.assign(rawRecord, store.Models);
        }
        return this.record;
    }

    /**
     * @param {string} name
     * @returns {RecordList}
     */
    ensureRecordList(name) {
        let recordList = this.fieldsList.get(name);
        if (!recordList) {
            recordList = new RecordList();
            Object.assign(recordList._, { name, owner: this.record });
            this.fieldsList.set(name, recordList);
        }
        return recordList;
    }

    /**
     * @param {Record} rawRecord
     * @param {string} name
     */
    proxyDeleteProperty(rawRecord, name) {
        const record = this.record;
        const Model = rawRecord.Model;
        if (Model._.parentFields.has(name)) {
            const parentFieldName = Model._.parentFields.get(name);
            const parentRecordProxy = record[parentFieldName];
            return Reflect.deleteProperty(parentRecordProxy, name);
        }
        if (
            !Model._.fields.get(name) &&
            !Model._.fieldsComputable.has(name) &&
            Object.hasOwn(rawRecord, name)
        ) {
            return Reflect.deleteProperty(rawRecord, name);
        }
        return Model.store._.MAKE_UPDATE(function recordDeleteProperty() {
            if (isRelation(Model, name)) {
                record._.ensureRecordList(name).clear();
                return true;
            }
            record._.ensureFieldSignal(name).set(undefined);
            return true;
        });
    }

    /**
     * @param {Record} rawRecord
     * @param {string} name
     */
    proxyGet(rawRecord, name) {
        if (name === "_") {
            return this;
        }
        if (typeof name === "symbol" || technicalKeysOnRecords.has(name)) {
            return Reflect.get(rawRecord, name, this.record);
        }
        const sig = this.fieldsAttrSignal.get(name);
        if (sig !== undefined) {
            const val = sig();
            if (
                typeof val === "object" &&
                val !== null &&
                rawRecord.Model._.fieldsAttrAsProxy.has(name)
            ) {
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
            let computedGetter = this.fieldsComputed.get(name);
            if (!computedGetter) {
                // the declaration sits on the record until its first read
                const { compute, msUntilStale, equals } = rawRecord[name];
                delete rawRecord[name];
                computedGetter = this.makeComputed(compute, msUntilStale, equals);
                this.fieldsComputed.set(name, computedGetter);
            }
            return computedGetter();
        }
        const parentFieldName = Model._.parentFields.get(name);
        if (parentFieldName) {
            const parentRecord = this.record[parentFieldName];
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
            const res = Reflect.get(rawRecord, name, this.record);
            // a model is a class, so a function: binding it would hide its statics
            if (typeof res === "function" && !res._) {
                return res.bind(this.record);
            }
            return res;
        }
        if (isRelation(Model, name)) {
            const recordList = this.ensureRecordList(name);
            if (isMany(Model, name)) {
                return recordList;
            }
            return recordList[0];
        }
        const val = this.ensureFieldSignal(name)();
        if (typeof val === "object" && val !== null && Model._.fieldsAttrAsProxy.has(name)) {
            return proxy(val);
        }
        return val;
    }

    /**
     * Route a plain data descriptor through the set trap, as patching a
     * record defines the field rather than sets it.
     *
     * @param {Record} rawRecord
     * @param {string|symbol} name
     * @param {PropertyDescriptor} descriptor
     */
    proxyDefineProperty(rawRecord, name, descriptor) {
        if (typeof name === "symbol") {
            return Reflect.defineProperty(rawRecord, name, descriptor);
        }
        if (technicalKeysOnRecords.has(name)) {
            // keep what the constructor set: `Store` redeclares `_` for typing
            return true;
        }
        if (!descriptor.enumerable || !descriptor.writable || !("value" in descriptor)) {
            return Reflect.defineProperty(rawRecord, name, descriptor);
        }
        return this.proxySet(rawRecord, name, descriptor.value);
    }

    /**
     * @param {Record} rawRecord
     * @param {string} name
     * @param {any} val
     */
    proxySet(rawRecord, name, val) {
        const record = this.record;
        const Model = rawRecord.Model;
        const store = rawRecord.store;
        if (isComputedDefinition(val)) {
            // the declaration sits on the record until its first read
            // defineProperty, as Reflect.set fails when a prototype has a getter of this name
            Model._.fieldsComputable.add(name);
            return Reflect.defineProperty(rawRecord, name, {
                configurable: true,
                enumerable: true,
                value: val,
                writable: true,
            });
        }
        if (isFieldDefinition(val)) {
            if (this.fieldsDeclared?.has(name)) {
                console.warn(
                    `Field "${name}" on model "${Model.getName()}" is already defined; the redefinition is ignored.`
                );
                return true;
            }
            this.fieldsDeclared?.add(name);
            if (!Model._.fields.get(name)) {
                Model._.prepareField(name, val);
            }
            if (isRelation(Model, name)) {
                this.ensureRecordList(name);
            } else {
                this.ensureFieldSignal(name, val);
            }
            return true;
        }
        if (!this.isConstructing()) {
            const parentFieldName = Model._.parentFields.get(name);
            if (parentFieldName) {
                const parentRecord = record[parentFieldName];
                return Reflect.set(parentRecord, name, val);
            }
        }
        if (
            this.isConstructing() &&
            typeof name === "string" &&
            !Model._.fields.get(name) &&
            !Model._.parentFields.has(name) &&
            !technicalKeysOnRecords.has(name)
        ) {
            Model._.prepareField(name, fields.Attr(val));
            this.ensureFieldSignal(name, val);
            return true;
        }
        if (
            Model._.fields.get(name) &&
            !isRelation(Model, name) &&
            !this.fieldsAttrSignal.has(name)
        ) {
            this.ensureFieldSignal(name, val);
            return true;
        }
        if (typeof name === "string" && !this.isDeclared(name)) {
            return this.setUndeclared(name, val, "written");
        }
        if (isRelation(Model, name)) {
            this.ensureRecordList(name);
        }
        const storeInternal = store._;
        return storeInternal.MAKE_UPDATE(function recordSet() {
            storeInternal.updateFields(record, { [name]: val });
            return true;
        });
    }

    /**
     * @param {string} name
     * @returns {boolean} whether the model of this record declares `name`
     */
    isDeclared(name) {
        const Model = this.record.Model;
        return (
            Boolean(Model._.fields.get(name)) ||
            Model._.fieldsComputable.has(name) ||
            technicalKeysOnRecords.has(name) ||
            versionKeys.has(name)
        );
    }

    /**
     * @param {string} name
     * @param {any} val
     * @param {"written"|"inserted"} verb
     * @returns {boolean}
     */
    setUndeclared(name, val, verb) {
        const record = this.record;
        for (
            let proto = Object.getPrototypeOf(record);
            proto && proto !== Object.prototype;
            proto = Object.getPrototypeOf(proto)
        ) {
            const descriptor = Object.getOwnPropertyDescriptor(proto, name);
            if (descriptor) {
                if (descriptor.set) {
                    return Reflect.set(proto, name, val, record);
                }
                if (descriptor.writable) {
                    return Reflect.defineProperty(record, name, {
                        configurable: true,
                        enumerable: false,
                        value: val,
                        writable: true,
                    });
                }
                break;
            }
        }
        console.warn(
            `Dropping unknown field "${name}" ${verb} on "${record.Model.getName()}": records only hold declared fields.`
        );
        return true;
    }
}

untrackFunctions(RecordInternal.prototype, [
    "ensureFieldSignal",
    "ensureRecordList",
    "proxyDeleteProperty",
    "proxySet",
    "setUndeclared",
]);
