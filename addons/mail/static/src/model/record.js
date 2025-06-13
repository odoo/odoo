import { markup, toRaw } from "@odoo/owl";
import {
    IS_DELETED_SYM,
    OR_SYM,
    isCommand,
    isMany,
    isOne,
    isRecord,
    isRelation,
    modelRegistry,
} from "./misc";
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
    static id;
    /** @type {import("@web/env").OdooEnv} */
    static env;
    /** @type {import("@web/env").OdooEnv} */
    env;
    /** @type {Object<string, Record>} */
    static records;
    /** @type {import("models").Store} */
    static store;
    /** @param {() => any} fn */
    static MAKE_UPDATE(fn) {
        return this.store.MAKE_UPDATE(...arguments);
    }
    static onChange(record, name, cb) {
        return this.store.onChange(...arguments);
    }
    static get(data) {
        const Model = toRaw(this);
        return this.records[Model.localId(data)];
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
        const Model = toRaw(this);
        let idStr;
        if (typeof data === "object" && data !== null) {
            idStr = Model._localId(Model.id, data);
        } else {
            idStr = data; // non-object data => single id
        }
        return `${Model.getName()},${idStr}`;
    }
    static _localId(expr, data, { brackets = false } = {}) {
        const Model = toRaw(this);
        if (!Array.isArray(expr)) {
            if (Model._.fields.get(expr)) {
                if (Model._.fieldsMany.get(expr)) {
                    throw new Error("Using a fields.Many() as id is not (yet) supported");
                }
                if (!isRelation(Model, expr)) {
                    return data[expr];
                }
                if (isCommand(data[expr])) {
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
        const Model = toRaw(this);
        const res = {};
        function _deepRetrieve(expr2) {
            if (typeof expr2 === "string") {
                if (isCommand(data[expr2])) {
                    // Note: only fields.One() is supported
                    const [cmd, data2] = data[expr2].at(-1);
                    return Object.assign(res, {
                        [expr2]:
                            cmd === "DELETE"
                                ? undefined
                                : cmd === "DELETE.noinv"
                                ? [["DELETE.noinv", data2]]
                                : cmd === "ADD.noinv"
                                ? [["ADD.noinv", data2]]
                                : data2,
                    });
                }
                return Object.assign(res, { [expr2]: data[expr2] });
            }
            if (expr2 instanceof Array) {
                for (const expr of this.id) {
                    if (typeof expr === "symbol") {
                        continue;
                    }
                    _deepRetrieve(expr);
                }
            }
        }
        if (Model.id === undefined) {
            return res;
        }
        if (typeof Model.id === "string") {
            if (typeof data !== "object" || data === null) {
                return { [Model.id]: data }; // non-object data => single id
            }
            if (isCommand(data[Model.id])) {
                // Note: only fields.One is supported
                const [cmd, data2] = data[Model.id].at(-1);
                return Object.assign(res, {
                    [Model.id]:
                        cmd === "DELETE"
                            ? undefined
                            : cmd === "DELETE.noinv"
                            ? [["DELETE.noinv", data2]]
                            : cmd === "ADD.noinv"
                            ? [["ADD.noinv", data2]]
                            : data2,
                });
            }
            return { [Model.id]: data[Model.id] };
        }
        for (const expr of Model.id) {
            if (typeof expr === "symbol") {
                continue;
            }
            _deepRetrieve(expr);
        }
        return res;
    }
    /**
     * Technical attribute, DO NOT USE in business code.
     * This class is almost equivalent to current class of model,
     * except this is a function, so we can new() it, whereas
     * `this` is not, because it's an object.
     * (in order to comply with OWL reactivity)
     *
     * @type {typeof Record}
     */
    static Class;
    /**
     * This method is almost equivalent to new Class, except that it properly
     * setup relational fields of model with get/set, @see Class
     *
     * @returns {Record}
     */
    static new(data, ids) {
        const Model = toRaw(this);
        const store = Model._rawStore;
        return store.MAKE_UPDATE(function RecordNew() {
            const recordProxy = new Model.Class();
            const record = toRaw(recordProxy)._raw;
            Object.assign(record._, { localId: Model.localId(ids) });
            Object.assign(recordProxy, { ...ids });
            Model.records[record.localId] = recordProxy;
            if (record.Model.getName() === "Store") {
                Object.assign(record, {
                    env: Model._rawStore.env,
                    recordByLocalId: Model._rawStore.recordByLocalId,
                });
            }
            Model._rawStore.recordByLocalId.set(record.localId, recordProxy);
            for (const fieldName of record.Model._.fields.keys()) {
                record._.requestCompute?.(record, fieldName);
                record._.requestSort?.(record, fieldName);
            }
            return recordProxy;
        });
    }
    /** @returns {Record|Record[]} */
    static insert(data, options = {}) {
        const ModelFullProxy = this;
        const Model = toRaw(ModelFullProxy);
        const store = Model._rawStore;
        return store.MAKE_UPDATE(function RecordInsert() {
            const isMulti = Array.isArray(data);
            if (!isMulti) {
                data = [data];
            }
            const res = data.map(function RecordInsertMap(d) {
                return Model._insert.call(ModelFullProxy, d, options);
            });
            if (!isMulti) {
                return res[0];
            }
            return res;
        });
    }
    /** @returns {Record} */
    static _insert(data) {
        const ModelFullProxy = this;
        const Model = toRaw(ModelFullProxy);
        const recordFullProxy = Model.preinsert.call(ModelFullProxy, data);
        const record = toRaw(recordFullProxy)._raw;
        record.update.call(record._proxy, data);
        return recordFullProxy;
    }
    /** @returns {Record} */
    static preinsert(data) {
        const ModelFullProxy = this;
        const Model = toRaw(ModelFullProxy);
        const ids = Model._retrieveIdFromData(data);
        for (const name in ids) {
            if (
                ids[name] &&
                !isRecord(ids[name]) &&
                !isCommand(ids[name]) &&
                isRelation(Model, name)
            ) {
                // preinsert that record in relational field,
                // as it is required to make current local id
                ids[name] = Model._rawStore[Model._.fieldsTargetModel.get(name)].preinsert(
                    ids[name]
                );
            }
        }
        return Model.get.call(ModelFullProxy, data) ?? Model.new(data, ids);
    }

    /** @returns {import("models").Store} */
    get store() {
        return toRaw(this)._raw.Model._rawStore._proxy;
    }
    /** @returns {import("models").Store} */
    get _rawStore() {
        return toRaw(this)._raw.Model._rawStore;
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
        return toRaw(this)._.localId;
    }
    /** @type {this} */
    _raw;
    /** @type {this} */
    _proxyInternal;
    /** @type {this} */
    _proxy;

    setup() {}

    update(data) {
        const record = toRaw(this)._raw;
        const store = record._rawStore;
        return store.MAKE_UPDATE(function recordUpdate() {
            if (typeof data === "object" && data !== null) {
                store._.updateFields(record, data);
            } else {
                if (Array.isArray(record.Model.id)) {
                    throw new Error(
                        `Cannot insert "${data}" on model "${record.Model.getName()}": this model doesn't support single-id data!`
                    );
                }
                // update on single-id data
                store._.updateFields(record, { [record.Model.id]: data });
            }
        });
    }

    delete() {
        const record = toRaw(this)._raw;
        const store = record._rawStore;
        return store.MAKE_UPDATE(function recordDelete() {
            store._.ADD_QUEUE("delete", record);
        });
    }

    exists() {
        return !this._[IS_DELETED_SYM];
    }

    /** @param {Record} record */
    eq(record) {
        return toRaw(this)._raw === toRaw(record)?._raw;
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
        return collection.some((record) => toRaw(record)._raw.eq(this));
    }

    /** @param {Record[]|RecordList} collection */
    notIn(collection) {
        return !this.in(collection);
    }

    /**
     * Converts the current record and its related data into Store insert-able data.
     * @param {Array<string> | { depth: boolean }} options Configuration options or an array of field names.
     * @returns {Object} A data object grouped by model names.
     */
    toData(options = { depth: false }) {
        const prefix = this._getActualModelName();
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
        const fieldsToDelete = [
            "_",
            "_fieldsValue",
            "_proxy",
            "_proxyInternal",
            "_raw",
            "env",
            "Model",
        ];
        fieldsToDelete.forEach((field) => delete data[field]);
    }

    _getActualModelName() {
        return this.Model.getName();
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
        const record = toRaw(recordProxy)._raw;
        const Model = record.Model;
        const data = { ...recordProxy };
        for (const name of Model._.fields.keys()) {
            const fullFieldName = prefix ? `${prefix}.${name}` : name;
            if (isMany(Model, name)) {
                data[name] = record._proxyInternal[name].map((recordProxy) => {
                    const record = toRaw(recordProxy)._raw;
                    return record._toDataRelationalRecord.call(
                        record._proxyInternal,
                        ongoing,
                        fullFieldName
                    );
                });
            } else if (isOne(Model, name)) {
                const otherRecord = toRaw(record._proxyInternal[name])?._raw;
                data[name] = otherRecord?._toDataRelationalRecord.call(
                    otherRecord._proxyInternal,
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
        const pyModelName = record._getActualModelName();
        ongoing.storeData[pyModelName] ||= [];
        ongoing.storeData[pyModelName].push(data);
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
