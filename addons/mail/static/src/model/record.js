import {
    computed,
    effect,
    immediateEffect,
    markRaw,
    markup,
    shallowEqual,
    untrack,
} from "@odoo/owl";
import {
    COMPUTED_SYM,
    OR_SYM,
    STORE_SYM,
    isCommandList,
    isMany,
    isOne,
    isRecord,
    isRelation,
    modelRegistry,
    technicalKeysOnRecords,
    untrackFunctions,
} from "./misc";
import { RecordInternal } from "./record_internal";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";

/** @typedef {import("./misc").FieldDefinition} FieldDefinition */
/** @typedef {import("./record_list").RecordList} RecordList */
/**
 * @typedef {Object} Ongoing
 * @property {Object} storeData Store insert-able data grouped by model names
 * @property {Set<string>} seenRecords A set of localIDs to track visited records
 * @property {boolean} depth Whether to recursively fetch deep data for all related records
 * @property {string[]} fields An array of field names to fetch, using dot notation (e.g., `"persona.group_ids"`).
 */

const Markup = markup().constructor;

export class Record {
    /** @type {import("./model_internal").ModelInternal} */
    static _;
    /** @type {import("./record_internal").RecordInternal} */
    _;
    static id = "id";
    /** @type {import("@web/env").OdooEnv} */
    static env;
    /** @type {import("@web/env").OdooEnv} */
    env;
    /** @type {Object<string, Record>} */
    static records;
    /** @type {import("models").Store} */
    static store;
    /** @type {string} */
    static _name;

    /** @param {Object} [ids] the identifying values, from `Record.new` */
    constructor(ids) {
        markRaw(this);
        const Model = new.target;
        this._raw = this;
        if (!Model._) {
            // the dummy record collecting the field declarations has no internals
            return;
        }
        this.Model = Model;
        this._ = this[STORE_SYM] ? Record.store._ : new RecordInternal();
        return this._.prepareRecord(this, ids);
    }

    /** @param {() => any} fn */
    static MAKE_UPDATE(fn) {
        return this.store.MAKE_UPDATE(...arguments);
    }
    static get(data) {
        const Model = this;
        return Model.records.get(Model.localId(data));
    }
    /**
     * Gets a record by id, fetching it from the server if it doesn't exist in the store or if some
     * of the specified fields are missing.
     * Only works for models that are explicitly supported in /mail/store controller.
     *
     * @param {number} id
     * @param {string[]} field_names
     */
    static async getOrFetch(id, field_names = []) {
        let record = this.get(id);
        if (!record || field_names.some((fieldName) => record[fieldName] === undefined)) {
            await this.store.fetchStoreData(this.getName(), { id });
            record = this.get(id);
            if (!record?.exists()) {
                return;
            }
        }
        return record;
    }
    static getName() {
        return this._name || this.name;
    }
    static register(localRegistry) {
        if (localRegistry) {
            // Record-specific tests use local registry as to not affect other tests
            localRegistry.add(this.getName(), this);
        } else {
            modelRegistry.add(this.getName(), this);
        }
    }
    static localId(data) {
        const Model = this;
        let idStr;
        if (Model.singleton) {
            return Model.getName();
        }
        if (typeof data === "object" && data !== null) {
            idStr = Model._localId(Model.id, data);
        } else {
            idStr = data; // non-object data => single id
        }
        return `${Model.getName()},${idStr}`;
    }
    static _localId(expr, data, { brackets = false } = {}) {
        const Model = this;
        if (!Array.isArray(expr)) {
            if (Model._.fields.get(expr)) {
                if (Model._.fieldsMany.get(expr)) {
                    throw new Error("Using a fields.Many() as id is not (yet) supported");
                }
                if (!isRelation(Model, expr)) {
                    return data[expr];
                }
                if (isCommandList(data[expr])) {
                    // Note: only fields.One is supported
                    const [cmd, data2] = data[expr].at(-1);
                    if (cmd === "DELETE") {
                        return undefined;
                    } else {
                        return `(${data2?.localId})`;
                    }
                }
                // relational field (note: optional when OR)
                if (isRecord(data[expr])) {
                    return `(${data[expr]?.localId})`;
                }
                const TargetModelName = Model._.fieldsTargetModel.get(expr);
                return `(${Model.store[TargetModelName].get(data[expr])?.localId})`;
            }
            return data[expr];
        }
        const vals = [];
        for (let i = 1; i < expr.length; i++) {
            vals.push(Model._localId(expr[i], data, { brackets: true }));
        }
        let res = vals.join(expr[0] === OR_SYM ? " OR " : " AND ");
        if (brackets) {
            res = `(${res})`;
        }
        return res;
    }
    static _retrieveIdFromData(data) {
        const Model = this;
        if (Model.singleton || Model.id === undefined) {
            return {};
        }
        function idValue(expr) {
            const val = data[expr];
            if (isCommandList(val)) {
                // Note: only fields.One() is supported
                const [cmd, data2] = val.at(-1);
                if (cmd === "DELETE") {
                    return undefined;
                }
                if (cmd === "DELETE.noinv") {
                    return [["DELETE.noinv", data2]];
                }
                if (cmd === "ADD.noinv") {
                    return [["ADD.noinv", data2]];
                }
                return data2;
            }
            return val;
        }
        if (typeof Model.id === "string") {
            if (typeof data !== "object" || data === null) {
                return { [Model.id]: data }; // non-object data => single id
            }
            return { [Model.id]: idValue(Model.id) };
        }
        const res = {};
        for (const expr of Model.id) {
            if (typeof expr === "symbol") {
                continue;
            }
            res[expr] = idValue(expr);
        }
        return res;
    }
    /**
     * This method is almost equivalent to constructor, except that it properly
     * setups all model concepts.
     *
     * @returns {Record}
     */
    static new(data, ids) {
        const Model = this;
        const store = Model._rawStore;
        return store.MAKE_UPDATE(function RecordNew() {
            const recordProxy = new Model(ids);
            const record = recordProxy._raw;
            recordProxy.setup();
            Object.assign(recordProxy, { ...ids });
            Model.records.set(record.localId, recordProxy);
            if (record.Model.getName() === "Store") {
                record.env = Model._rawStore.env;
            }
            // compute inherits fields in priority, as other fields might depend on them
            for (const fieldName of Model._.inheritsFields) {
                record._.compute?.(fieldName);
            }
            for (const fieldName of record.Model._.fields.keys()) {
                record._.requestCompute?.(fieldName);
            }
            record._.isConstructing.set(false);
            return recordProxy;
        });
    }
    /** @returns {Record|Record[]} */
    static insert(data, options = {}) {
        const Model = this;
        const store = Model._rawStore;
        return store.MAKE_UPDATE(function RecordInsert() {
            const isMulti = Array.isArray(data);
            if (!isMulti) {
                data = [data];
            }
            const res = data.map(function RecordInsertMap(d) {
                return Model._insert(d, options);
            });
            if (!isMulti) {
                return res[0];
            }
            return res;
        });
    }
    /** @returns {Record} */
    static _insert(data) {
        const Model = this;
        const recordProxy = Model.preinsert(data);
        const record = recordProxy._raw;
        record.update.call(record._proxy, data, { forceApply: false });
        return recordProxy;
    }
    /** @returns {Record} */
    static preinsert(data) {
        const Model = this;
        const ids = Model._retrieveIdFromData(data);
        if (!Model.singleton) {
            for (const name in ids) {
                if (
                    ids[name] &&
                    !isRecord(ids[name]) &&
                    !isCommandList(ids[name]) &&
                    isRelation(Model, name)
                ) {
                    // preinsert that record in relational field,
                    // as it is required to make current local id
                    ids[name] = Model._rawStore[Model._.fieldsTargetModel.get(name)].preinsert(
                        ids[name]
                    );
                }
            }
        }
        return Model.get(data) ?? Model.new(data, ids);
    }

    /** @returns {import("models").Store} */
    get store() {
        return this._raw.Model._rawStore._proxy;
    }
    /** @returns {import("models").Store} */
    get _rawStore() {
        return this._raw.Model._rawStore;
    }
    /**
     * Technical attribute, contains the Model entry in the store.
     * This is almost the same as the class, except it's an object
     * (so it works with OWL reactivity), and it's the actual object
     * that store the records.
     *
     * Indeed, `this.constructor.records` is there to initiate `records`
     * on the store entry, but the class `static records` is not actually
     * used because it's non-reactive, and we don't want to persistently
     * store records on class, to make sure different tests do not share
     * records.
     *
     * @type {typeof Record}
     */
    Model;
    /** @type {string} */
    get localId() {
        return this._.localId;
    }
    /** @type {this} */
    _raw;
    /** @type {this} */
    _proxy;

    setup() {}

    /**
     * Declares a value computed from the record, read like a field without
     * being one: the value lives in an owl computed, and the model neither
     * stores nor serializes it.
     *
     * @template T
     * @param {() => T} compute
     * @returns {T}
     */
    computed(compute) {
        return { [COMPUTED_SYM]: true, compute };
    }

    /**
     * Declares a computed whose value goes stale on its own, a value read
     * from the clock in particular: `msUntilStale` gives the delay after
     * which the value is made again, or nothing to leave it as it is. The
     * value is made again while it is read and schedules nothing once nobody
     * reads it.
     *
     * @template T
     * @param {() => T} compute
     * @param {(value: T) => number|void} msUntilStale
     * @returns {T}
     */
    computedUntilStale(compute, msUntilStale) {
        return { ...this.computed(compute), msUntilStale };
    }

    /**
     * @param {Object|any} data
     * @param {Object} [options={}]
     * @param {boolean} [options.forceApply=true] Apply the data even when the
     * current insert version is out of order. Only versioned server data turns
     * it off.
     */
    update(data, { forceApply = true } = {}) {
        const record = this._raw;
        const store = record._rawStore;
        return store.MAKE_UPDATE(function recordUpdate() {
            if (typeof data === "object" && data !== null) {
                store._.updateFields(record, data, { forceApply });
            } else {
                if (Array.isArray(record.Model.id)) {
                    throw new Error(
                        `Cannot insert "${data}" on model "${record.Model.getName()}": this model doesn't support single-id data!`
                    );
                }
                // update on single-id data
                store._.updateFields(record, { [record.Model.id]: data }, { forceApply });
            }
        });
    }

    delete() {
        const record = this._raw;
        if (!record.exists()) {
            return;
        }
        const store = record._rawStore;
        return store.MAKE_UPDATE(function recordDelete() {
            // delete records inheriting the current record before deleting the current record
            for (const fieldName of record.Model._.inheritsInverseFields) {
                if (record.Model._.fieldsMany.get(fieldName)) {
                    const dependentRecordListProxy = record._proxy[fieldName];
                    for (const dependentRecordProxy of dependentRecordListProxy) {
                        store._.ADD_QUEUE("delete", dependentRecordProxy._raw);
                    }
                } else {
                    const dependentRecordProxy = record._proxy[fieldName];
                    if (dependentRecordProxy) {
                        store._.ADD_QUEUE("delete", dependentRecordProxy._raw);
                    }
                }
            }
            store._.ADD_QUEUE("delete", record);
        });
    }

    exists() {
        return !this._.isDeleted();
    }

    /** @param {Record} record */
    eq(record) {
        return this._raw === record?._raw;
    }

    /** @param {Record} record */
    notEq(record) {
        return !this.eq(record);
    }

    /** @param {Record[]|RecordList} collection */
    in(collection) {
        if (!collection) {
            return false;
        }
        return collection.some((record) => record._raw.eq(this));
    }

    /** @param {Record[]|RecordList} collection */
    notIn(collection) {
        return !this.in(collection);
    }

    /**
     * Run `callback` with the values returned by `dependencies`, again each
     * time one of those values changes, until the record is deleted.
     *
     * The values are compared with `shallowEqual`, so a derived value that
     * stays equal runs nothing. Both functions are bound to the record proxy.
     *
     * @template {any[]} T
     * @param {(this: this) => T} dependencies tracking is exactly what it reads
     *  while it runs: read `.length` or iterate in it if the content of a list
     *  matters
     * @param {(this: this, ...deps: T) => (() => void)|void} callback may return
     *  a cleanup function, invoked before the next callback and on dispose
     * @param {Object} [options]
     * @param {boolean} [options.immediate=false] use owl's synchronous
     *  `immediateEffect` instead of the default batched `effect`
     * @param {boolean} [options.initialRun=true] pass false to skip the first run
     */
    onChange(dependencies, callback, { immediate = false, initialRun = true } = {}) {
        const record = this;
        if (!record._) {
            // the dummy record collecting the field declarations has no internals
            return;
        }
        const deps = record._.ensureScope().run(() =>
            computed(dependencies.bind(record), { equals: shallowEqual })
        );
        const boundCallback = (...values) => callback.apply(record._proxy, values);
        let firstRun = true;
        let cleanup;
        record._registerDisposeFn(
            immediateEffect(function onChangeAfterConstructing() {
                if (untrack(() => record._.isConstructing())) {
                    // deps and initial run wait for a complete record
                    void record._.isConstructing();
                    return;
                }
                const effectFn = immediate ? immediateEffect : effect;
                const disposeFn = untrack(() =>
                    effectFn(function runOnChange() {
                        const values = deps() ?? [];
                        if (firstRun) {
                            firstRun = false;
                            if (!initialRun) {
                                return;
                            }
                        }
                        untrack(() => {
                            cleanup?.();
                            const result = boundCallback(...values);
                            cleanup = typeof result === "function" ? result : undefined;
                        });
                    })
                );
                record._registerDisposeFn(() => {
                    disposeFn();
                    untrack(() => cleanup?.());
                    cleanup = undefined;
                });
            })
        );
    }

    /**
     * Converts the current record and its related data into Store insert-able data.
     * @param {Array<string> | { depth: boolean }} options Configuration options or an array of field names.
     * @returns {Object} A data object grouped by model names.
     */
    toData(options = { depth: false }) {
        const prefix = this.Model.getName();
        const ongoing = {
            seenRecords: new Set(),
            storeData: {},
            depth: options.depth,
            fields: undefined,
        };
        if (Array.isArray(options)) {
            ongoing.fields = options.map((field) => `${prefix}.${field}`);
        }
        this._toData(ongoing, prefix);
        return ongoing.storeData;
    }

    _cleanupData(data) {
        technicalKeysOnRecords.forEach((field) => delete data[field]);
    }

    /** @param {Function} disposeFn */
    _registerDisposeFn(disposeFn) {
        this._.disposeFns.add(disposeFn);
        if (!this[STORE_SYM]) {
            this.store._.disposeFns.add(disposeFn);
        }
    }

    /** @param {Function} f */
    _runDisposeFn(f) {
        f();
        this._.disposeFns.delete(f);
        if (!this[STORE_SYM]) {
            this.store._.disposeFns.delete(f);
        }
    }

    _runDisposeFns() {
        for (const f of this._.disposeFns) {
            this._runDisposeFn(f);
        }
        // after the effects, so that none of them recomputes a disposed computed
        this._.scope?.destroy();
    }

    /**
     * @param {Ongoing} ongoing The ongoing data conversion state.
     * @param {string} [prefix] The prefix for the current field (used for nested fields).
     */
    _toData(ongoing, prefix = undefined) {
        if (ongoing.depth && ongoing.seenRecords.has(this.localId)) {
            return;
        }
        ongoing.seenRecords.add(this.localId);

        const recordProxy = this;
        const record = recordProxy._raw;
        const Model = record.Model;
        const data = { ...recordProxy };
        for (const name of Model._.fields.keys()) {
            if (Model._.fieldsCompute.has(name)) {
                delete data[name];
                continue;
            }
            const fullFieldName = prefix ? `${prefix}.${name}` : name;
            if (isMany(Model, name)) {
                data[name] = record._proxy[name].map((recordProxy) => {
                    const record = recordProxy._raw;
                    return record._toDataRelationalRecord.call(
                        record._proxy,
                        ongoing,
                        fullFieldName
                    );
                });
            } else if (isOne(Model, name)) {
                const otherRecord = record._proxy[name]?._raw;
                data[name] = otherRecord?._toDataRelationalRecord.call(
                    otherRecord._proxy,
                    ongoing,
                    fullFieldName
                );
            } else {
                // fields.Attr()
                const value = recordProxy[name];
                if (Model._.fieldsType.get(name) === "datetime" && value) {
                    data[name] = serializeDateTime(value);
                } else if (Model._.fieldsType.get(name) === "date" && value) {
                    data[name] = serializeDate(value);
                } else if (Model._.fieldsHtml.get(name) && value instanceof Markup) {
                    data[name] = ["markup", value.toString()];
                } else {
                    data[name] = value;
                }
            }
        }

        this._cleanupData(data);
        const modelName = record.Model.getName();
        ongoing.storeData[modelName] ||= [];
        ongoing.storeData[modelName].push(data);
    }

    /**
     * @param {Ongoing} ongoing The ongoing data conversion state.
     * @param {string} prefix The prefix for the current field (used for nested fields).
     * @returns {Object} A data object grouped by model names.
     */
    _toDataRelationalRecord(ongoing, prefix = undefined) {
        const data = this.Model._retrieveIdFromData(this);
        if (ongoing.depth || ongoing.fields?.some((field) => field.startsWith(prefix))) {
            this._toData(ongoing, prefix);
        }
        for (const [name, val] of Object.entries(data)) {
            if (isRecord(val)) {
                data[name] = val._toDataRelationalRecord(ongoing, prefix);
            }
        }
        return data;
    }
}
Record.register();

untrackFunctions(Record, ["insert", "new"]);
untrackFunctions(Record.prototype, ["delete", "update"]);
