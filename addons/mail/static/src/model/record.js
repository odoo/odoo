import { toRaw } from "@odoo/owl";
import {
    ATTR_SYM,
    FIELD_DEFINITION_SYM,
    IS_DELETED_SYM,
    MANY_SYM,
    ONE_SYM,
    OR_SYM,
    isCommand,
    isMany,
    isOne,
    isRecord,
    isRelation,
    modelRegistry,
} from "./misc";

/** @typedef {import("./misc").FieldDefinition} FieldDefinition */
/** @typedef {import("./misc").RecordField} RecordField */
/** @typedef {import("./record_list").RecordList} RecordList */

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
                    throw new Error("Using a Record.Many() as id is not (yet) supported");
                }
                if (!isRelation(Model, expr)) {
                    return data[expr];
                }
                if (isCommand(data[expr])) {
                    // Note: only Record.one() is supported
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
                    // Note: only Record.one() is supported
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
                // Note: only Record.one() is supported
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
    /**
     * @template {keyof import("models").Models} M
     * @param {M} targetModel
     * @param {Object} [param1={}]
     * @param {(this: Record) => any} [param1.compute] if set, the value of this relational field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @param {boolean} [param1.eager=false] when field is computed, determines whether the computation
     *   of this field is eager or lazy. By default, fields are computed lazily, which means that
     *   they are computed when dependencies change AND when this field is being used. In eager mode,
     *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
     *   behaviour of OWL reactive.
     * @param {string} [param1.inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(this: Record, r: import("models").Models[M]) => void} [param1.onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(this: Record, r: import("models").Models[M]) => void} [param1.onDelete] function that is called when a record is removed
     *   from the relation.
     * @param {(this: Record) => void} [param1.onUpdate] function that is called when the field value is updated.
     *   This is called at least once at record creation.
     * @returns {import("models").Models[M]}
     */
    static one(targetModel, param1) {
        return { ...param1, targetModel, [FIELD_DEFINITION_SYM]: true, [ONE_SYM]: true };
    }
    /**
     * @template {keyof import("models").Models} M
     * @param {M} targetModel
     * @param {Object} [param1={}]
     * @param {(this: Record) => any} [param1.compute] if set, the value of this relational field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @param {boolean} [param1.eager=false] when field is computed, determines whether the computation
     *   of this field is eager or lazy. By default, fields are computed lazily, which means that
     *   they are computed when dependencies change AND when this field is being used. In eager mode,
     *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
     *   behaviour of OWL reactive.
     * @param {string} [param1.inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(this: Record, r: import("models").Models[M]) => void} [param1.onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(this: Record, r: import("models").Models[M]) => void} [param1.onDelete] function that is called when a record is removed
     *   from the relation.
     * @param {(this: Record) => void} [param1.onUpdate] function that is called when the field value is updated.
     *   This is called at least once at record creation.
     * @param {(this: Record, r1: import("models").Models[M], r2: import("models").Models[M]) => number} [param1.sort] if defined, this field
     *   is automatically sorted by this function.
     * @returns {import("models").Models[M][]}
     */
    static many(targetModel, param1) {
        return { ...param1, targetModel, [FIELD_DEFINITION_SYM]: true, [MANY_SYM]: true };
    }
    /**
     * @template T
     * @param {T} def
     * @param {Object} [param1={}]
     * @param {(this: Record) => any} [param1.compute] if set, the value of this attr field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @param {boolean} [param1.eager=false] when field is computed, determines whether the computation
     *   of this field is eager or lazy. By default, fields are computed lazily, which means that
     *   they are computed when dependencies change AND when this field is being used. In eager mode,
     *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
     *   behaviour of OWL reactive.
     * @param {boolean} [param1.html] if set, the field value contains html value.
     *   Useful to automatically markup when the insert is trusted.
     * @param {(this: Record) => void} [param1.onUpdate] function that is called when the field value is updated.
     *   This is called at least once at record creation.
     * @param {(this: Record, Object, Object) => number} [param1.sort] if defined, this field is automatically sorted
     *   by this function.
     * @param {'datetime'|'date'} [param1.type] if defined, automatically transform to a
     * specific type.
     * @returns {T}
     */
    static attr(def, param1) {
        return { ...param1, [FIELD_DEFINITION_SYM]: true, [ATTR_SYM]: true, default: def };
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
            const oldTrusted = store._.trusted;
            store._.trusted = options.html ?? store._.trusted;
            const res = data.map(function RecordInsertMap(d) {
                return Model._insert.call(ModelFullProxy, d, options);
            });
            store._.trusted = oldTrusted;
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

    toData() {
        const recordProxy = this;
        const record = toRaw(recordProxy)._raw;
        const Model = record.Model;
        const data = { ...recordProxy };
        for (const name of Model._.fields.keys()) {
            if (isMany(Model, name)) {
                data[name] = record._proxyInternal[name].map((recordProxy) => {
                    const record = toRaw(recordProxy)._raw;
                    return record.toIdData.call(record._proxyInternal);
                });
            } else if (isOne(Model, name)) {
                const otherRecord = toRaw(record._proxyInternal[name])?._raw;
                data[name] = otherRecord?.toIdData.call(record._proxyInternal);
            } else {
                data[name] = recordProxy[name]; // Record.attr()
            }
        }
        delete data._;
        delete data._fieldsValue;
        delete data._proxy;
        delete data._proxyInternal;
        delete data._raw;
        delete data.Model;
        return data;
    }
    toIdData() {
        const data = this.Model._retrieveIdFromData(this);
        for (const [name, val] of Object.entries(data)) {
            if (isRecord(val)) {
                data[name] = val.toIdData();
            }
        }
        return data;
    }
}
Record.register();
