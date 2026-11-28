import { getScope, signal } from "@odoo/owl";
import { isRelational, isX2Many, normalizeField } from "./fields";
import {
    ATOMS,
    BUILD,
    CHANGES,
    DELETED,
    FLAGS,
    HANDLES,
    ID,
    MODEL,
    Model,
    NEW,
    OWNER,
    PARENT,
    STUB,
    VALUES,
    composeClasses,
    getDeclaredFields,
    getDeclaredIndexes,
    getModelName,
} from "./model";

/** @import { ModelClass } from "./model" */

/**
 * @typedef {import("./fields").StoreField} StoreField
 *
 * @typedef {{
 *  name: string;
 *  store: Store;
 *  Record: ModelClass;
 *  checked: boolean;
 *  fields: StoreField[];
 *  fieldsByName: Record<string, StoreField>;
 *  editable: boolean;
 *  reactivity: "field" | "model";
 *  records: Map<number | string, Model>;
 *  indexes: Map<string, Map<any, Model>>;
 *  atom: ReturnType<typeof signal>;
 *  membership: ReturnType<typeof signal>;
 *  list: Model[] | null;
 * }} ModelMeta
 *
 * @typedef {Store | Draft} Owner
 *
 * @typedef {ModelClass | string} ModelRef a model, as its class or its name
 */

/**
 * @template M
 * @typedef {import("./fields").RecordValues<M>} RecordValues
 */

//-----------------------------------------------------------------------------
// Reactivity
//-----------------------------------------------------------------------------

// Values are not stored in signals: signals are empty "ticks" used to
// subscribe (read) and to wake subscribers (trigger). Values are computed on
// read from plain storage (see `read`).

/**
 * @param {Model} rec
 * @param {StoreField} field
 */
function track(rec, field) {
    const model = rec[MODEL];
    if (model.reactivity === "model") {
        model.atom();
    } else {
        const atoms = (rec[ATOMS] ||= []);
        (atoms[field.index] ||= signal(0))();
    }
}

/**
 * @param {Model} rec
 * @param {StoreField} field
 */
function notify(rec, field) {
    const model = rec[MODEL];
    if (model.reactivity === "model") {
        signal.trigger(model.atom);
    } else {
        const atom = rec[ATOMS]?.[field.index];
        if (atom) {
            signal.trigger(atom);
        }
    }
}

/**
 * The function a record exposes for a field: call it to read, `set` to write.
 * Created on first access and cached on the record, so that it is stable.
 *
 * @param {Model} rec
 * @param {StoreField} field
 * @returns {import("./fields").FieldSignal<any>}
 */
function getFieldSignal(rec, field) {
    const handles = (rec[HANDLES] ||= []);
    let fieldSignal = handles[field.index];
    if (!fieldSignal) {
        fieldSignal = () => read(rec, field);
        fieldSignal.set = (value) => writeField(rec, field, value);
        handles[field.index] = fieldSignal;
    }
    return fieldSignal;
}

//-----------------------------------------------------------------------------
// Reading and writing field values
//-----------------------------------------------------------------------------

/**
 * Tracked read: local change, else the parent's value (forks), else the last
 * server value.
 *
 * @param {Model} rec
 * @param {StoreField} field
 */
function read(rec, field) {
    track(rec, field);
    const change = rec[CHANGES]?.get(field.index);
    if (change) {
        return change.value;
    }
    const parent = rec[PARENT];
    if (parent) {
        return /** @type {Draft} */ (rec[OWNER]).adoptValue(field, read(parent, field));
    }
    return rec[VALUES][field.index];
}

/**
 * Untracked read, same rules as {@link read}.
 *
 * @param {Model} rec
 * @param {StoreField} field
 */
export function peek(rec, field) {
    const change = rec[CHANGES]?.get(field.index);
    if (change) {
        return change.value;
    }
    const parent = rec[PARENT];
    if (parent) {
        return /** @type {Draft} */ (rec[OWNER]).adoptValue(field, peek(parent, field));
    }
    return rec[VALUES][field.index];
}

/**
 * Local write: a change on editable models and in drafts, else a direct write.
 *
 * @param {Model} rec
 * @param {StoreField} field
 * @param {any} value
 */
function setLocal(rec, field, value) {
    const previous = peek(rec, field);
    const store = rec[MODEL].store;
    if (rec[OWNER] instanceof Draft || rec[MODEL].editable) {
        rec[CHANGES] ||= new Map();
        rec[CHANGES].set(field.index, { value, version: ++store.clock });
        signal.trigger(store.dirtyAtom);
    } else {
        rec[VALUES][field.index] = value;
    }
    afterWrite(rec, field, previous);
}

/**
 * Server write: updates the last server value. A local change on the same
 * field keeps shadowing it.
 *
 * @param {Model} rec
 * @param {StoreField} field
 * @param {any} value
 */
function setBase(rec, field, value) {
    const previous = peek(rec, field);
    rec[VALUES][field.index] = value;
    afterWrite(rec, field, previous);
}

/**
 * @param {Model} rec
 * @param {StoreField} field
 * @param {any} previous
 */
function afterWrite(rec, field, previous) {
    if (field.indexed && rec[OWNER] === rec[MODEL].store) {
        reindex(rec, field, previous);
    }
    notify(rec, field);
}

/** How inverse sync reads and writes: local changes, or last server values. */
const LOCAL = { get: peek, set: setLocal };
const BASE = {
    get: (/** @type {Model} */ rec, /** @type {StoreField} */ field) => rec[VALUES][field.index],
    set: setBase,
};

/**
 * @param {any} a
 * @param {any} b
 */
function sameValue(a, b) {
    if (a === b) {
        return true;
    }
    if (Array.isArray(a) && Array.isArray(b)) {
        return a.length === b.length && a.every((value, i) => value === b[i]);
    }
    return false;
}

/**
 * Turns what callers give for a relational value (a record, an id, a values
 * object, false) into a record of the given owner.
 *
 * @param {Owner} owner
 * @param {ModelMeta} comodel
 * @param {any} value
 * @param {typeof LOCAL | typeof BASE} mode
 * @returns {Model | null}
 */
function toRecord(owner, comodel, value, mode) {
    if (value === null || value === undefined || value === false) {
        return null;
    }
    if (value instanceof Model) {
        return owner.own(value);
    }
    if (typeof value === "object") {
        if (mode === BASE) {
            return /** @type {Store} */ (owner)._loadRecord(comodel, value);
        }
        return "id" in value
            ? owner.get(comodel.name, value.id, true)
            : owner.create(comodel.name, value);
    }
    return owner.get(comodel.name, value, true);
}

/**
 * @param {Owner} owner
 * @param {StoreField} field
 * @param {any} value
 * @param {typeof LOCAL | typeof BASE} mode
 */
function normalize(owner, field, value, mode) {
    switch (field.type) {
        case "many2one":
            return toRecord(owner, field.comodel, value, mode);
        case "one2many":
        case "many2many":
            return (value || []).map((v) => toRecord(owner, field.comodel, v, mode));
        default:
            return value;
    }
}

/**
 * Public local write, used by field setters.
 *
 * @param {Model} rec
 * @param {StoreField} field
 * @param {any} value
 */
function writeField(rec, field, value) {
    if (rec[FLAGS] & DELETED) {
        throw new Error(`Cannot write on deleted record ${rec[MODEL].name}(${rec[ID]})`);
    }
    const newValue = normalize(rec[OWNER], field, value, LOCAL);
    const oldValue = peek(rec, field);
    if (sameValue(oldValue, newValue)) {
        return;
    }
    setLocal(rec, field, newValue);
    syncInverse(rec, field, oldValue, newValue, LOCAL);
}

/**
 * @param {Model} rec
 * @param {Record<string, any>} values
 */
function updateRecord(rec, values) {
    const model = rec[MODEL];
    for (const name in values) {
        const field = model.fieldsByName[name];
        if (!field) {
            throw new Error(`Unknown field "${name}" on model "${model.name}"`);
        }
        writeField(rec, field, values[name]);
    }
}

/**
 * Sets the initial values of a new record. x2many lists start loaded and
 * empty, so that inverse sync can add to them.
 *
 * @param {Model} rec
 * @param {ModelMeta} model
 * @param {Record<string, any>} values
 */
function initRecord(rec, model, values) {
    for (const name in values) {
        if (name !== "id" && !(name in model.fieldsByName)) {
            throw new Error(`Unknown field "${name}" on model "${model.name}"`);
        }
    }
    for (const field of model.fields) {
        if (isX2Many(field)) {
            rec[VALUES][field.index] = [];
        }
    }
    for (const field of model.fields) {
        if (field.name in values) {
            writeField(rec, field, values[field.name]);
        } else if (field.default !== undefined) {
            const value = typeof field.default === "function" ? field.default(rec) : field.default;
            writeField(rec, field, value);
        }
    }
}

//-----------------------------------------------------------------------------
// Relations
//-----------------------------------------------------------------------------

/**
 * Keeps the other side of a relation in sync. Lists that are not loaded are
 * left alone: we don't know their full content.
 *
 * @param {Model} rec
 * @param {StoreField} field
 * @param {any} oldValue
 * @param {any} newValue
 * @param {typeof LOCAL | typeof BASE} mode
 */
function syncInverse(rec, field, oldValue, newValue, mode) {
    const inverse = field.inverseField;
    if (!inverse) {
        return;
    }
    if (field.type === "many2one") {
        if (oldValue) {
            removeFromList(oldValue, inverse, rec, mode);
        }
        if (newValue) {
            addToList(newValue, inverse, rec, mode);
        }
        return;
    }
    const oldSet = new Set(oldValue || []);
    const newSet = new Set(newValue || []);
    for (const target of oldSet) {
        if (newSet.has(target)) {
            continue;
        }
        if (field.type === "one2many") {
            if (mode.get(target, inverse) === rec) {
                mode.set(target, inverse, null);
            }
        } else {
            removeFromList(target, inverse, rec, mode);
        }
    }
    for (const target of newSet) {
        if (oldSet.has(target)) {
            continue;
        }
        if (field.type === "one2many") {
            const previousParent = mode.get(target, inverse);
            if (previousParent === rec) {
                continue;
            }
            if (previousParent) {
                removeFromList(previousParent, field, target, mode);
            }
            mode.set(target, inverse, rec);
        } else {
            addToList(target, inverse, rec, mode);
        }
    }
}

/**
 * @param {Model} target
 * @param {StoreField} field
 * @param {Model} item
 * @param {typeof LOCAL | typeof BASE} mode
 */
function addToList(target, field, item, mode) {
    const list = mode.get(target, field);
    if (list && !list.includes(item)) {
        mode.set(target, field, [...list, item]);
    }
}

/**
 * @param {Model} target
 * @param {StoreField} field
 * @param {Model} item
 * @param {typeof LOCAL | typeof BASE} mode
 */
function removeFromList(target, field, item, mode) {
    const list = mode.get(target, field);
    if (list?.includes(item)) {
        mode.set(
            target,
            field,
            list.filter((r) => r !== item)
        );
    }
}

/**
 * Removes a record from the other side of its relations, as local writes.
 *
 * @param {Model} rec
 */
function unlinkRelations(rec) {
    for (const field of rec[MODEL].fields) {
        if (!field.inverseField) {
            continue;
        }
        const value = peek(rec, field);
        if (value && (!Array.isArray(value) || value.length)) {
            syncInverse(rec, field, value, isX2Many(field) ? [] : null, LOCAL);
        }
    }
}

//-----------------------------------------------------------------------------
// Indexes
//-----------------------------------------------------------------------------

/**
 * @param {any} key
 */
function isIndexKey(key) {
    return key !== undefined && key !== null && key !== false;
}

/**
 * @param {Model} rec
 * @param {StoreField} field
 * @param {any} previous value before the write
 */
function reindex(rec, field, previous) {
    const index = rec[MODEL].indexes.get(field.name);
    const current = peek(rec, field);
    if (previous === current) {
        return;
    }
    if (isIndexKey(previous) && index.get(previous) === rec) {
        index.delete(previous);
    }
    if (isIndexKey(current)) {
        index.set(current, rec);
    }
}

//-----------------------------------------------------------------------------
// Store
//-----------------------------------------------------------------------------

/** `status` of a destroyed Owl scope */
const SCOPE_DESTROYED = 2;

/**
 * @param {ModelClass} RecordClass
 * @param {Owner} owner
 * @param {number | string} id
 * @param {number} flags
 * @param {Model | null} parent
 */
function construct(RecordClass, owner, id, flags, parent) {
    return new RecordClass(BUILD, owner, id, flags, parent);
}

/**
 * One object per (model, id), relations as record objects, local changes kept
 * apart from the last server values, drafts as overlays.
 */
export class Store {
    clock = 0;
    virtualId = 0;
    /** @type {Map<string, ModelMeta>} */
    models = new Map();
    /** coarse signal for dirty state: triggered on every local change, ack and discard */
    dirtyAtom = signal(0);
    /**
     * The Owl scope the store is created in (a plugin, a component), if any.
     * Records are built inside it, so that the class fields of a model can call
     * hooks such as `usePlugin`.
     */
    scope = getScope();

    /**
     * The models of a store are the ones of the given classes, with the fields
     * they declare: a store knows nothing else. A relation has to target one
     * of these models.
     *
     * @param {{ models?: ModelClass[] }} [params]
     */
    constructor({ models = [] } = {}) {
        for (const [name, ModelClass] of composeClasses(models)) {
            this.models.set(name, this._setupModel(name, ModelClass));
        }
        for (const model of this.models.values()) {
            this._resolveRelations(model);
        }
    }

    // Public
    //-------------------------------------------------------------------------

    /**
     * @param {Model} rec
     */
    ack(rec, version = Infinity) {
        this._ackRecord(this.own(rec), version);
        signal.trigger(this.dirtyAtom);
    }

    /**
     * Creates a record, with a temporary id unless `values` has one.
     *
     * @template {ModelClass} C
     * @overload
     * @param {C} model
     * @param {RecordValues<InstanceType<C>>} [values]
     * @returns {InstanceType<C>}
     */
    /**
     * @template {Model} [M=Model]
     * @overload
     * @param {string} model
     * @param {NoInfer<RecordValues<M>>} [values]
     * @returns {M}
     */
    /**
     * @param {ModelRef} modelRef
     * @param {Record<string, any>} [values]
     */
    create(modelRef, values = {}) {
        const model = this.model(modelRef);
        const id = values.id ?? `virtual_${++this.virtualId}`;
        if (model.records.has(id)) {
            throw new Error(`Record ${model.name}(${id}) already exists`);
        }
        const rec = this._newRecord(model, id, model.editable ? NEW : 0);
        initRecord(rec, model, values);
        rec.setup();
        return rec;
    }

    /**
     * @param {Model} rec
     */
    delete(rec) {
        rec = this.own(rec);
        const model = rec[MODEL];
        unlinkRelations(rec);
        if (model.editable && !(rec[FLAGS] & NEW)) {
            // keep a tombstone until the deletion is acknowledged
            rec[FLAGS] |= DELETED;
            this._membershipChanged(model);
            signal.trigger(this.dirtyAtom);
        } else {
            this._forget(rec);
        }
    }

    /**
     * Drops the local changes of a record and of its one2many children.
     *
     * @param {Model} rec
     */
    discard(rec) {
        this._discardRecord(this.own(rec));
        signal.trigger(this.dirtyAtom);
    }

    draft() {
        return new Draft(this);
    }

    /**
     * @template {ModelClass} C
     * @overload
     * @param {C} model
     * @param {number | string} id
     * @param {boolean} [stub] create an empty record if the id is unknown
     * @returns {InstanceType<C> | null}
     */
    /**
     * @template {Model} [M=Model]
     * @overload
     * @param {string} model
     * @param {number | string} id
     * @param {boolean} [stub]
     * @returns {M | null}
     */
    /**
     * @param {ModelRef} modelRef
     * @param {number | string} id
     * @param {boolean} [stub]
     * @returns {Model | null}
     */
    get(modelRef, id, stub = false) {
        const model = this.model(modelRef);
        const rec = model.records.get(id);
        if (rec) {
            return rec[FLAGS] & DELETED ? null : rec;
        }
        if (!stub) {
            return null;
        }
        const newStub = this._newRecord(model, id, STUB);
        newStub.setup();
        return newStub;
    }

    /**
     * Lookup through a unique index, declared with the `indexes` of a model.
     *
     * @template {ModelClass} C
     * @overload
     * @param {C} model
     * @param {string} fieldName
     * @param {any} value
     * @returns {InstanceType<C> | null}
     */
    /**
     * @template {Model} [M=Model]
     * @overload
     * @param {string} model
     * @param {string} fieldName
     * @param {any} value
     * @returns {M | null}
     */
    /**
     * @param {ModelRef} modelRef
     * @param {string} fieldName
     * @param {any} value
     * @returns {Model | null}
     */
    getBy(modelRef, fieldName, value) {
        const model = this.model(modelRef);
        const index = model.indexes.get(fieldName);
        if (!index) {
            throw new Error(`Field "${model.name}.${fieldName}" is not indexed`);
        }
        return index.get(value) || null;
    }

    /**
     * @param {Model} rec
     */
    isDirty(rec) {
        this.dirtyAtom();
        return Boolean(rec[CHANGES]?.size || rec[FLAGS] & (NEW | DELETED));
    }

    /**
     * @param {Model} rec
     */
    isNew(rec) {
        return Boolean(rec[FLAGS] & NEW);
    }

    /**
     * Merges server data: `load({ model: [values] })`, or
     * `load(model, values | values[])`. Values update the last server values;
     * local changes keep shadowing them.
     *
     * @param {ModelRef | Record<string, Record<string, any>[]>} modelRefOrData
     * @param {Record<string, any> | Record<string, any>[]} [values]
     * @returns {any} the loaded record(s), when called with a model
     */
    load(modelRefOrData, values) {
        if (typeof modelRefOrData === "object") {
            for (const [modelName, list] of Object.entries(modelRefOrData)) {
                this.load(modelName, list);
            }
            return;
        }
        const model = this.model(modelRefOrData);
        return Array.isArray(values)
            ? values.map((v) => this._loadRecord(model, v))
            : this._loadRecord(model, values);
    }

    /**
     * @param {ModelRef} modelRef
     * @returns {ModelMeta}
     */
    model(modelRef) {
        const name = typeof modelRef === "string" ? modelRef : getModelName(modelRef);
        const model = this.models.get(name);
        if (!model) {
            throw new Error(`Unknown model "${name}"`);
        }
        return model;
    }

    /**
     * @template {Model} M
     * @param {M} rec
     * @returns {M}
     */
    own(rec) {
        if (rec[OWNER] !== this) {
            throw new Error(
                `Record ${rec[MODEL].name}(${rec[ID]}) belongs to another store or draft`
            );
        }
        return rec;
    }

    /**
     * Live records of a model: loaded or created, not deleted. Reactive to
     * creations and deletions, not to field changes.
     *
     * @template {ModelClass} C
     * @overload
     * @param {C} model
     * @returns {InstanceType<C>[]}
     */
    /**
     * @template {Model} [M=Model]
     * @overload
     * @param {string} model
     * @returns {M[]}
     */
    /**
     * @param {ModelRef} modelRef
     * @returns {Model[]}
     */
    records(modelRef) {
        const model = this.model(modelRef);
        model.membership();
        model.list ||= [...model.records.values()].filter((r) => !(r[FLAGS] & (STUB | DELETED)));
        return model.list;
    }

    /**
     * Replaces a temporary id by the server id. The record object stays the
     * same, so every relation pointing to it stays valid.
     *
     * @param {Model} rec
     * @param {number | string} newId
     */
    rekey(rec, newId) {
        const model = this.own(rec)[MODEL];
        if (model.records.has(newId)) {
            throw new Error(`Record ${model.name}(${newId}) already exists`);
        }
        model.records.delete(rec[ID]);
        rec[ID] = newId;
        model.records.set(newId, rec);
    }

    /**
     * @template {Model} M
     * @param {M} rec
     * @param {RecordValues<M>} values
     */
    update(rec, values) {
        updateRecord(this.own(rec), values);
    }

    // Private
    //-------------------------------------------------------------------------

    /**
     * @param {Model} rec
     * @param {number} version
     */
    _ackRecord(rec, version) {
        const model = rec[MODEL];
        const changes = rec[CHANGES];
        for (const field of model.fields) {
            if (field.type !== "one2many") {
                continue;
            }
            const change = changes?.get(field.index);
            const base = rec[VALUES][field.index] || [];
            const sent = change && change.version <= version ? change.value : base;
            for (const child of sent) {
                this._ackRecord(child, version);
            }
            for (const child of base) {
                if (!sent.includes(child)) {
                    // removed from the list: deleted on the server
                    this._forget(child);
                }
            }
        }
        if (changes) {
            for (const [index, change] of changes) {
                if (change.version <= version) {
                    rec[VALUES][index] = change.value;
                    changes.delete(index);
                }
            }
            if (!changes.size) {
                rec[CHANGES] = null;
            }
        }
        rec[FLAGS] &= ~NEW;
        if (rec[FLAGS] & DELETED) {
            this._forget(rec);
        }
    }

    /**
     * @param {Model} rec
     */
    _discardRecord(rec) {
        const model = rec[MODEL];
        for (const field of model.fields) {
            if (field.type === "one2many") {
                const children = new Set([
                    ...(peek(rec, field) || []),
                    ...(rec[VALUES][field.index] || []),
                ]);
                for (const child of children) {
                    this._discardRecord(child);
                }
            }
        }
        if (rec[FLAGS] & NEW) {
            this._forget(rec);
            return;
        }
        const changes = rec[CHANGES];
        if (rec[FLAGS] & DELETED) {
            rec[FLAGS] &= ~DELETED;
            this._membershipChanged(model);
        }
        if (changes) {
            const previous = [...changes.keys()].map((index) => peek(rec, model.fields[index]));
            rec[CHANGES] = null;
            [...changes.keys()].forEach((index, i) =>
                afterWrite(rec, model.fields[index], previous[i])
            );
        }
    }

    /**
     * Removes a record from the store for good.
     *
     * @param {Model} rec
     */
    _forget(rec) {
        const model = rec[MODEL];
        for (const [fieldName, index] of model.indexes) {
            const key = peek(rec, model.fieldsByName[fieldName]);
            if (isIndexKey(key) && index.get(key) === rec) {
                index.delete(key);
            }
        }
        rec[FLAGS] |= DELETED;
        model.records.delete(rec[ID]);
        this._membershipChanged(model);
    }

    /**
     * Builds a record object, for this store or for one of its drafts.
     *
     * @param {ModelMeta} model
     * @param {Owner} owner
     * @param {number | string} id
     * @param {number} flags
     * @param {Model | null} parent
     * @returns {Model}
     */
    _build(model, owner, id, flags, parent) {
        const scope = this.scope;
        const rec =
            scope && scope.status < SCOPE_DESTROYED
                ? scope.run(construct, model.Record, owner, id, flags, parent)
                : new model.Record(BUILD, owner, id, flags, parent);
        if (!model.checked) {
            model.checked = true;
            for (const key of Object.keys(rec)) {
                if (key in model.fieldsByName) {
                    throw new Error(
                        `Field "${model.name}.${key}" is hidden by a class field of the same name`
                    );
                }
            }
        }
        return rec;
    }

    /**
     * @param {ModelMeta} model
     * @param {Record<string, any>} values
     */
    _loadRecord(model, values) {
        if (!("id" in values)) {
            throw new Error(`Cannot load a ${model.name} record without id`);
        }
        let rec = model.records.get(values.id);
        const isNewObject = !rec;
        if (!rec) {
            rec = this._newRecord(model, values.id, 0);
        } else if (rec[FLAGS] & STUB) {
            rec[FLAGS] &= ~STUB;
            this._membershipChanged(model);
        }
        for (const name in values) {
            if (name === "id") {
                continue;
            }
            const field = model.fieldsByName[name];
            if (!field) {
                throw new Error(`Unknown field "${name}" on model "${model.name}"`);
            }
            const newValue = normalize(this, field, values[name], BASE);
            const oldValue = rec[VALUES][field.index];
            if (sameValue(oldValue, newValue)) {
                continue;
            }
            setBase(rec, field, newValue);
            syncInverse(rec, field, oldValue, newValue, BASE);
        }
        if (isNewObject) {
            rec.setup();
        }
        return rec;
    }

    /**
     * @param {ModelMeta} model
     */
    _membershipChanged(model) {
        model.list = null;
        signal.trigger(model.membership);
    }

    /**
     * @param {ModelMeta} model
     * @param {number | string} id
     * @param {number} flags
     */
    _newRecord(model, id, flags) {
        const rec = this._build(model, this, id, flags, null);
        rec[VALUES] = new Array(model.fields.length);
        model.records.set(id, rec);
        if (!(flags & STUB)) {
            this._membershipChanged(model);
        }
        return rec;
    }

    /**
     * @param {ModelMeta} model
     */
    _resolveRelations(model) {
        for (const field of model.fields) {
            if (!isRelational(field)) {
                continue;
            }
            const comodel = this.models.get(field.relation);
            if (!comodel) {
                throw new Error(
                    `Field "${model.name}.${field.name}" targets unknown model "${field.relation}"`
                );
            }
            field.comodel = comodel;
            if (!field.inverse) {
                continue;
            }
            const inverse = comodel.fieldsByName[field.inverse];
            const expectedType =
                field.type === "many2many"
                    ? "many2many"
                    : field.type === "many2one"
                    ? "one2many"
                    : "many2one";
            if (!inverse || inverse.type !== expectedType) {
                throw new Error(
                    `Invalid inverse "${comodel.name}.${field.inverse}" for field "${model.name}.${field.name}"`
                );
            }
            if (inverse.inverse && inverse.inverse !== field.name) {
                throw new Error(
                    `Fields "${model.name}.${field.name}" and "${comodel.name}.${inverse.name}" disagree on their inverse`
                );
            }
            // an inverse declared on one side only is mirrored on the other
            inverse.inverse = field.name;
            inverse.inverseField = field;
            field.inverseField = inverse;
        }
    }

    /**
     * @param {string} name
     * @param {ModelClass} ModelClass
     * @returns {ModelMeta}
     */
    _setupModel(name, ModelClass) {
        const fields = Object.entries(getDeclaredFields(ModelClass)).map(
            ([fieldName, declaration], index) => normalizeField(fieldName, declaration, index)
        );

        if (!["field", "model"].includes(ModelClass._reactivity)) {
            throw new Error(`Invalid reactivity "${ModelClass._reactivity}" on model "${name}"`);
        }

        // per-store subclass: holds the field getters, so that stores don't share state
        const RecordClass = class extends ModelClass {};
        /** @type {ModelMeta} */
        const model = {
            name,
            store: this,
            Record: RecordClass,
            checked: false,
            fields,
            fieldsByName: Object.fromEntries(fields.map((f) => [f.name, f])),
            editable: ModelClass._editable,
            reactivity: /** @type {"field" | "model"} */ (ModelClass._reactivity),
            records: new Map(),
            indexes: new Map(),
            atom: signal(0),
            membership: signal(0),
            list: null,
        };
        RecordClass.prototype[MODEL] = model;
        for (const field of fields) {
            if (field.name in ModelClass.prototype) {
                throw new Error(`Field "${name}.${field.name}" clashes with a class member`);
            }
            Object.defineProperty(RecordClass.prototype, field.name, {
                get() {
                    return getFieldSignal(this, field);
                },
            });
        }
        for (const fieldName of getDeclaredIndexes(ModelClass)) {
            const field = model.fieldsByName[fieldName];
            if (!field || isRelational(field)) {
                throw new Error(`Cannot index field "${name}.${fieldName}"`);
            }
            field.indexed = true;
            model.indexes.set(fieldName, new Map());
        }
        return model;
    }
}

//-----------------------------------------------------------------------------
// Drafts
//-----------------------------------------------------------------------------

/**
 * An overlay on a store or on another draft. Records of the parent are forked
 * on first access: forks read through to the parent and keep their own
 * changes. `commit()` replays them as local writes on the parent.
 */
export class Draft {
    /** @type {Map<Model, Model>} parent record -> fork */
    forks = new Map();
    /** @type {Map<number | string, Model>} records created in this draft */
    created = new Map();
    /** @type {WeakMap<Model[], Model[]>} parent x2many lists -> forked lists */
    lists = new WeakMap();
    membership = signal(0);

    /**
     * @param {Owner} parent
     */
    constructor(parent) {
        this.parent = parent;
        /** @type {Store} */
        this.store = parent instanceof Draft ? parent.store : parent;
    }

    /**
     * @param {StoreField} field
     * @param {any} value a value of the parent
     */
    adoptValue(field, value) {
        if (!isRelational(field) || !value) {
            return value;
        }
        if (field.type === "many2one") {
            return this.own(value);
        }
        let list = this.lists.get(value);
        if (!list) {
            list = value.map((rec) => this.own(rec));
            this.lists.set(value, list);
        }
        return list;
    }

    commit() {
        const parent = this.parent;
        /** @type {Map<Model, Model>} */
        const toParent = new Map();
        for (const [parentRec, fork] of this.forks) {
            toParent.set(fork, parentRec);
        }
        // create first, so that relations between new records can be mapped
        for (const rec of this.created.values()) {
            toParent.set(rec, parent.create(rec[MODEL].name, { id: rec[ID] }));
        }
        const mapValue = (/** @type {StoreField} */ field, /** @type {any} */ value) => {
            if (!isRelational(field)) {
                return value;
            }
            return field.type === "many2one"
                ? value && toParent.get(value)
                : value.map((/** @type {Model} */ r) => toParent.get(r));
        };
        const writeBack = (/** @type {Model} */ rec) => {
            const target = toParent.get(rec);
            for (const [index, change] of rec[CHANGES] || []) {
                const field = rec[MODEL].fields[index];
                writeField(target, field, mapValue(field, change.value));
            }
        };
        const forks = [...this.forks.values()];
        for (const fork of forks) {
            if (!(fork[FLAGS] & DELETED)) {
                writeBack(fork);
            }
        }
        for (const rec of this.created.values()) {
            writeBack(rec);
        }
        for (const fork of forks) {
            if (fork[FLAGS] & DELETED) {
                parent.delete(toParent.get(fork));
            }
        }
        // the draft's objects now read through to the parent
        for (const rec of this.created.values()) {
            rec[PARENT] = toParent.get(rec);
            this.forks.set(rec[PARENT], rec);
        }
        this.created.clear();
        for (const fork of this.forks.values()) {
            fork[CHANGES] = null;
            fork[FLAGS] = 0;
        }
        signal.trigger(this.membership);
        signal.trigger(this.store.dirtyAtom);
    }

    /**
     * @template {ModelClass} C
     * @overload
     * @param {C} model
     * @param {RecordValues<InstanceType<C>>} [values]
     * @returns {InstanceType<C>}
     */
    /**
     * @template {Model} [M=Model]
     * @overload
     * @param {string} model
     * @param {NoInfer<RecordValues<M>>} [values]
     * @returns {M}
     */
    /**
     * @param {ModelRef} modelRef
     * @param {Record<string, any>} [values]
     */
    create(modelRef, values = {}) {
        const model = this.store.model(modelRef);
        const id = values.id ?? `virtual_${++this.store.virtualId}`;
        const rec = this.store._build(model, this, id, NEW, null);
        rec[VALUES] = new Array(model.fields.length);
        this.created.set(id, rec);
        initRecord(rec, model, values);
        rec.setup();
        signal.trigger(this.membership);
        return rec;
    }

    /**
     * @param {Model} rec
     */
    delete(rec) {
        rec = this.own(rec);
        unlinkRelations(rec);
        if (rec[FLAGS] & NEW) {
            this.created.delete(rec[ID]);
        }
        rec[FLAGS] |= DELETED;
        signal.trigger(this.membership);
    }

    discard() {
        for (const fork of this.forks.values()) {
            const changes = fork[CHANGES];
            fork[CHANGES] = null;
            fork[FLAGS] = 0;
            for (const index of changes?.keys() || []) {
                notify(fork, fork[MODEL].fields[index]);
            }
        }
        this.created.clear();
        signal.trigger(this.membership);
        signal.trigger(this.store.dirtyAtom);
    }

    draft() {
        return new Draft(this);
    }

    /**
     * @template {ModelClass} C
     * @overload
     * @param {C} model
     * @param {number | string} id
     * @param {boolean} [stub]
     * @returns {InstanceType<C> | null}
     */
    /**
     * @template {Model} [M=Model]
     * @overload
     * @param {string} model
     * @param {number | string} id
     * @param {boolean} [stub]
     * @returns {M | null}
     */
    /**
     * @param {ModelRef} modelRef
     * @param {number | string} id
     * @param {boolean} [stub]
     * @returns {Model | null}
     */
    get(modelRef, id, stub = false) {
        const modelName = this.store.model(modelRef).name;
        const created = this.created.get(id);
        if (created && created[MODEL].name === modelName) {
            return created;
        }
        const rec = this.parent.get(modelName, id, stub);
        return rec && this.own(rec);
    }

    isDirty() {
        this.store.dirtyAtom();
        this.membership();
        if (this.created.size) {
            return true;
        }
        for (const fork of this.forks.values()) {
            if (fork[CHANGES]?.size || fork[FLAGS] & DELETED) {
                return true;
            }
        }
        return false;
    }

    /**
     * Returns the fork of a record of this draft's parent (or of an ancestor).
     *
     * @template {Model} M
     * @param {M} rec
     * @returns {M}
     */
    own(rec) {
        if (rec[OWNER] === this) {
            return rec;
        }
        if (rec[OWNER] !== this.parent) {
            rec = this.parent.own(rec);
        }
        let fork = this.forks.get(rec);
        if (!fork) {
            // built like any record, so that its class fields (computed values,
            // local state) read the values of this draft
            fork = this.store._build(rec[MODEL], this, rec[ID], 0, rec);
            this.forks.set(rec, fork);
            fork.setup();
        }
        return /** @type {M} */ (fork);
    }

    /**
     * @template {ModelClass} C
     * @overload
     * @param {C} model
     * @returns {InstanceType<C>[]}
     */
    /**
     * @template {Model} [M=Model]
     * @overload
     * @param {string} model
     * @returns {M[]}
     */
    /**
     * @param {ModelRef} modelRef
     * @returns {Model[]}
     */
    records(modelRef) {
        const modelName = this.store.model(modelRef).name;
        this.membership();
        /** @type {Model[]} */
        const result = [];
        const parentRecords = this.parent.records(modelName);
        for (const rec of parentRecords) {
            const fork = this.own(rec);
            if (!(fork[FLAGS] & DELETED)) {
                result.push(fork);
            }
        }
        for (const rec of this.created.values()) {
            if (rec[MODEL].name === modelName && !(rec[FLAGS] & DELETED)) {
                result.push(rec);
            }
        }
        return result;
    }

    /**
     * @template {Model} M
     * @param {M} rec
     * @param {RecordValues<M>} values
     */
    update(rec, values) {
        updateRecord(this.own(rec), values);
    }
}
