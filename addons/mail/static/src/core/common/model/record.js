import { RecordList } from "./record_list";
import {
    ATTR_SYM,
    MANY_SYM,
    ONE_SYM,
    modelRegistry,
    _0,
    isRecord,
    FIELD_DEFINITION_SYM,
    RECORD_DELETED_SYM,
} from "./misc";

export class Record {
    /**
     * Expression to define how records on the model are identified.
     * Supported value:
     * - string with single field name
     * - non-nested AND/OR expressions with field names. see AND|OR functions
     * - list with the above values except OR expression (each items are disjunctive, i.e. joined with OR)
     *
     * @type {string|AND|OR|Array<string|AND>}
     */
    static id;
    /**
     * key is the local objectId, basically ModelName{number}, e.g. "Persona{200}"
     *
     * @type {Object<string, Record>}
     */
    static records;
    /** @type {import("models").Store} */
    static store;
    /** @type {import("models").Store} */
    static store0;
    /**
     * Whether there's only at most 1 record of this model.
     * Useful to simply insert on such record without having to define a dummy id and making sure it's the same value passed.
     * `undefined` values are not elligible as non-local object id, and non-singleton models will refuse to insert a record
     * without at least one non-local object id.
     */
    static singleton = false;
    /** @param {() => any} fn */
    static MAKE_UPDATE(fn) {
        return this.store0.MAKE_UPDATE(fn);
    }
    static onChange(record, name, cb) {
        const store0 = this.store0;
        return store0._onChange(record, name, (observe) => {
            const fn = () => {
                observe();
                cb();
            };
            if (store0._.UPDATE !== 0) {
                if (!store0._.RO_QUEUE.has(fn)) {
                    store0._.RO_QUEUE.set(fn, true);
                }
            } else {
                fn();
            }
        });
    }
    /** @type {import("./model_internal").ModelInternal} */
    static _;
    static isRecord(record) {
        return isRecord(record);
    }
    static get(data) {
        const this0 = _0(this);
        return this.records[this0._.dataToLocalId(this0, data)];
    }
    static register() {
        modelRegistry.add(this.name, this);
    }
    /**
     * This method is almost equivalent to new Class, except that it properly
     * setup relational fields of model with get/set, @see Class
     *
     * @returns {Record}
     */
    static new(data) {
        const this0 = _0(this);
        const store0 = this0.store0;
        return store0.MAKE_UPDATE(function R_new() {
            const rec1 = new this0._.Class();
            const rec0 = _0(rec1);
            const localId = `${this0.name}{${this0._.NEXT_LOCAL_ID++}}`;
            Object.assign(rec0._, {
                localIds: [localId],
                objectIds: [localId],
            });
            this0.records[rec0.localId] = rec1;
            if (rec0.Model.name === "Store") {
                Object.assign(rec0, {
                    env: store0.env,
                    objectIdToLocalId: store0.objectIdToLocalId,
                    localIdToRecord: store0.localIdToRecord,
                });
            }
            store0.localIdToRecord.set(rec0.localId, rec1);
            store0.objectIdToLocalId.set(rec0.localId, rec0.localId);
            for (const fieldName of rec0.Model._.fields.keys()) {
                rec0._.requestComputeField(rec0, fieldName);
                rec0._.requestSortField(rec0, fieldName);
            }
            return rec1;
        });
    }
    /**
     * @template {keyof import("models").Models} M
     * @param {M} targetModel
     * @param {Object} [param1={}]
     * @param {Function} [param1.compute] if set, the value of this relational field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @param {boolean} [param1.eager=false] when field is computed, determines whether the computation
     *   of this field is eager or lazy. By default, fields are computed lazily, which means that
     *   they are computed when dependencies change AND when this field is being used. In eager mode,
     *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
     *   behaviour of OWL reactive.
     * @param {string} [param1.inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(r: import("models").Models[M]) => void} [param1.onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(r: import("models").Models[M]) => void} [param1.onDelete] function that is called when a record is removed
     *   from the relation.
     * @param {() => void} [param1.onUpdate] function that is called when the field value is updated.
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
     * @param {Function} [param1.compute] if set, the value of this relational field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @param {boolean} [param1.eager=false] when field is computed, determines whether the computation
     *   of this field is eager or lazy. By default, fields are computed lazily, which means that
     *   they are computed when dependencies change AND when this field is being used. In eager mode,
     *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
     *   behaviour of OWL reactive.
     * @param {string} [param1.inverse] if set, the name of field in targetModel that acts as the inverse.
     * @param {(r: import("models").Models[M]) => void} [param1.onAdd] function that is called when a record is added
     *   in the relation.
     * @param {(r: import("models").Models[M]) => void} [param1.onDelete] function that is called when a record is removed
     *   from the relation.
     * @param {() => void} [param1.onUpdate] function that is called when the field value is updated.
     *   This is called at least once at record creation.
     * @param {(r1: import("models").Models[M], r2: import("models").Models[M]) => number} [param1.sort] if defined, this field
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
     * @param {Function} [param1.compute] if set, the value of this attr field is declarative and
     *   is computed automatically. All reactive accesses recalls that function. The context of
     *   the function is the record. Returned value is new value assigned to this field.
     * @param {boolean} [param1.eager=false] when field is computed, determines whether the computation
     *   of this field is eager or lazy. By default, fields are computed lazily, which means that
     *   they are computed when dependencies change AND when this field is being used. In eager mode,
     *   the field is immediately (re-)computed when dependencies changes, which matches the built-in
     *   behaviour of OWL reactive.
     * @param {boolean} [param1.html] if set, the field value contains html value.
     *   Useful to automatically markup when the insert is trusted.
     * @param {() => void} [param1.onUpdate] function that is called when the field value is updated.
     *   This is called at least once at record creation.
     * @param {(Object, Object) => number} [param1.sort] if defined, this field is automatically sorted
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
        const this3 = this;
        const this0 = _0(this3);
        const store0 = this0.store0;
        return store0.MAKE_UPDATE(function R_insert() {
            const isMulti = Array.isArray(data);
            if (!isMulti) {
                data = [data];
            }
            const oldTrusted = store0._.trusted;
            store0._.trusted = options.html ?? store0._.trusted;
            const res = data.map(function R_insert_map(d) {
                return this0._insert.call(this3, d, options);
            });
            store0._.trusted = oldTrusted;
            if (!isMulti) {
                return res[0];
            }
            return res;
        });
    }
    /** @returns {Record} */
    static _insert(data) {
        const this3 = this;
        const this0 = _0(this3);
        const record3 = this0.preinsert.call(this3, data);
        const record = _0(record3);
        record.update.call(record._2, data);
        return record3;
    }
    /**
     * @param {Object} data
     * @returns {Record}
     */
    static preinsert(data) {
        const this3 = this;
        const this0 = _0(this3);
        return this0.get.call(this3, data) ?? this0.new(data);
    }
    // Internal props on instance. Important to not have them being registered as fields!
    static get INSTANCE_INTERNALS() {
        return {
            Model: true,
            _0: true,
            _1: true,
            _2: true,
            _: true,
        };
    }
    /** @type {import("./record_internal").RecordInternal} */
    _;
    get _store() {
        return _0(this).Model.store0._2;
    }
    /** should be called in 0-mode! */
    get _store0() {
        return this.Model.store0;
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
    /**
     * The referenced local id of the record.
     *
     * local object id:
     *    ModelName{number}
     *    e.g. "Persona{20}"
     *
     * @type {string}
     */
    get localId() {
        return _0(this)._.localIds[0];
    }
    /** @type {this} */
    _0; // previously "_raw"
    /** @type {this} */
    _1; // previously "_proxyInternal"
    /** @type {this} */
    _2; // previously "_proxy"

    constructor() {
        this.setup();
    }

    setup() {}

    update(data) {
        if (data === undefined) {
            return;
        }
        const this0 = _0(this);
        return this0._store0.MAKE_UPDATE(function R_update() {
            if (typeof data === "object" && data !== null) {
                this0._store0._.update(this0, data);
            } else {
                // update on single-id data
                const singleIds = this0.Model._.singleIds;
                if (singleIds.length !== 1) {
                    throw new Error(`
                        Model "${this0.name}" has more than one single-id.
                        Shorthand to get/insert records with non-object is only supported with a single single-id.
                        Found singleIds: ${singleIds.map((item) => item[0]).join(",")}
                    `);
                }
                this0._store0._.update(this0, { [singleIds[0]]: data });
            }
        });
    }

    delete() {
        const this0 = _0(this);
        return this0._store0.MAKE_UPDATE(function R_delete() {
            this0._store0._.ADD_QUEUE("delete", this0);
        });
    }

    exists() {
        return !this[RECORD_DELETED_SYM];
    }

    /** @param {Record} record */
    eq(record) {
        const this0 = _0(this);
        const record0 = _0(record);
        if (!record?.localId) {
            return;
        }
        for (const thisLocalId of this0._.localIds || []) {
            for (const recordLocalId of record0._.localIds || []) {
                if (thisLocalId === recordLocalId) {
                    return true;
                }
            }
        }
        return false;
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
        if (collection instanceof RecordList) {
            return collection.includes(this);
        }
        // Array
        return collection.some((record) => _0(record).eq(this));
    }

    /** @param {Record[]|RecordList} collection */
    notIn(collection) {
        return !this.in(collection);
    }

    toData() {
        const this0 = _0(this);
        const data = { ...this };
        for (const [name, value] of Object.entries(this0)) {
            if (!this.Model._.fields.has(name)) {
                continue;
            }
            if (this0.Model._.fieldsMany.get(name)) {
                data[name] = value.map((record2) => {
                    const record = _0(record2);
                    return record.toIdData.call(record._1);
                });
            } else if (this0.Model._.fieldsOne.get(name)) {
                const record = _0(value[0]);
                data[name] = record?.toIdData.call(record._1);
            } else {
                data[name] = this[name]; // attr()
            }
        }
        for (const key of Object.keys(this0.Model.INSTANCE_INTERNALS)) {
            delete data[key];
        }
        return data;
    }
    toIdData() {
        const data = this._.retrieveIdValue(_0(this));
        for (const [name, val] of Object.entries(data)) {
            if (isRecord(val)) {
                data[name] = val.toIdData();
            }
        }
        return data;
    }
}

Record.register();
