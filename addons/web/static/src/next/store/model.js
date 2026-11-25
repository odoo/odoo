import { FIELD } from "./fields";

/**
 * A record of any model.
 *
 * @typedef {_Model} Model
 */

/**
 * A model class: `Model`, or any class that derives from it.
 *
 * @typedef {typeof _Model} ModelClass
 */

/**
 * The class an extension of the model class `C` derives from: its records have
 * the fields `F` on top of the ones of `C`. It only exists for types: at
 * runtime, it is `C` itself. See the example on `Model`.
 *
 * @template {abstract new (...args: any) => any} C
 * @template F
 * @typedef {Omit<C, "fields"> & { fields: any }
 *  & (new (...args: any[]) => InstanceType<C> & FieldsOf<F>)} Extension
 */

// Record slots. Symbols keep them out of the way of field names, which live on
// the prototype as getters returning field signals.
export const MODEL = Symbol("model"); // on the per-store prototype: the model meta
export const ID = Symbol("id");
export const OWNER = Symbol("owner"); // the store or draft the record belongs to
export const VALUES = Symbol("values"); // last server values, by field index; undefined = not loaded
export const CHANGES = Symbol("changes"); // null | Map<fieldIndex, { value, version }>
export const ATOMS = Symbol("atoms"); // subscription ticks, created on first read
export const HANDLES = Symbol("handles"); // field signals, created on first access
export const FLAGS = Symbol("flags");
export const PARENT = Symbol("parent"); // draft copies only: the record this one overlays

export const NEW = 1; // created locally, not saved yet
export const DELETED = 2;
export const STUB = 4; // referenced by id, nothing loaded yet

/** What a store passes to the constructor: records are only built by a store. */
export const BUILD = Symbol("build");

// Declaring a model:
//
//     /** @extends {Model<typeof Partner.fields>} */
//     export class Partner extends Model {
//         static _name = "res.partner";
//         static fields = {
//             name: fields.Char(),
//         };
//
//         label = computed(() => `[${this.id}] ${this.name()}`);
//     }
//
// Extending it, in another addon:
//
//     /** @import { Extension } from "@web/next/store/model" */
//
//     const mailPartnerFields = {
//         im_status: fields.Char(),
//     };
//
//     export class MailPartner extends /** @type {Extension<typeof Partner, typeof mailPartnerFields>} */ (
//         Partner
//     ) {
//         static _inherit = "res.partner";
//         static fields = mailPartnerFields;
//     }

/**
 * Base class of all store records.
 *
 * A model is declared by a class with a `_name` and `fields`. The class can
 * have per-record state and methods. Its `@extends` tag types the fields on
 * the records: without it, they are all `any`. See the examples above.
 *
 * Fields are read by calling them and written with `set`: `partner.name()`,
 * `partner.name.set("Bob")`. `partner.name` is a stable per-record function,
 * so it can be passed around like a signal (e.g. to `t-model`).
 *
 * Another addon extends a model with a class that has an `_inherit`, like in
 * Python. To type the fields it adds, the class derives from the class it
 * extends, cast to `Extension`. Otherwise, it can simply derive from `Model`.
 *
 * All the classes of a model are chained in registration order, like the
 * Python registry does, and `super` follows the chain.
 *
 * Records are built by a store, never with `new` in application code. Class
 * fields run when the record is built, before its values are set: code that
 * needs the values right away goes in `setup()`.
 */
class _Model {
    /** @type {string} name of the model this class declares */
    static _name = "";
    /** @type {string} name of the model this class extends */
    static _inherit = "";
    /**
     * Field declarations, see `fields.js`: the fields of the model, or the
     * ones an extension adds to it.
     *
     * @type {Record<string, any>}
     */
    static fields = {};
    /**
     * Records are edited locally and saved back. A local write is then kept
     * as a change, apart from the last server value: that is what `isDirty`,
     * `discard`, `ack` and `toCommands` work on. When false, a write replaces
     * the value: for data the client only mirrors. An extension can set it
     * too: the last class of the model wins.
     */
    static _editable = false;
    /**
     * How reads subscribe: to each field of each record, or to the whole model
     * (one subscription for all its records, for large read-mostly data). The
     * last class of the model wins.
     *
     * @type {string} "field" or "model"
     */
    static _reactivity = "field";
    /**
     * Names of non-relational fields with a unique index, see `store.getBy`.
     * The indexes of an extension are added to the ones of the model.
     *
     * @type {string[]}
     */
    static _indexes = [];

    /**
     * @param {symbol} key the store's `BUILD` token
     * @param {import("./store").Owner} owner
     * @param {number | string} id
     * @param {number} flags
     * @param {Model | null} parent
     */
    constructor(key, owner, id, flags, parent) {
        if (key !== BUILD) {
            throw new Error(
                `Records are built by a store: use store.create() or store.load(), not new ${
                    this.constructor.name ||
                    getModelName(/** @type {ModelClass} */ (this.constructor))
                }()`
            );
        }
        this[ID] = id;
        this[OWNER] = owner;
        // set by the store: an array for a record of a store, null for the copy
        // a draft makes of it (it reads through to its parent)
        /** @type {any} */
        this[VALUES] = null;
        /** @type {any} */
        this[CHANGES] = null;
        /** @type {any} */
        this[ATOMS] = null;
        /** @type {any} */
        this[HANDLES] = null;
        this[FLAGS] = flags;
        this[PARENT] = parent;
    }

    /** @returns {number | string} */
    get id() {
        return this[ID];
    }

    /**
     * The store or draft this record belongs to, e.g. to create related
     * records from a model method.
     *
     * @returns {import("./store").Owner}
     */
    get store() {
        return this[OWNER];
    }

    /**
     * Called once per record object, after its values are set: when it is
     * created, loaded or referenced in a store, and when a draft makes its own
     * copy of it.
     */
    setup() {}
}

/**
 * The fields `F` as record members. It is a mapped type on purpose: without
 * type argument, `F` is `any` in JS, and the members are then all `any`
 * instead of making the whole record `any`.
 *
 * @template F
 * @typedef {{ [K in keyof F]: F[K] }} FieldsOf
 */

/**
 * `Model<F>` types the fields `F` on the records, see the example above.
 *
 * It is `_Model`, with a generic constructor instead of its own: a class can
 * only take type arguments in `@extends` when its base constructor is generic.
 *
 * @type {{ [K in keyof typeof _Model]: (typeof _Model)[K] }
 *  & (new <F = {}>(...args: any[]) => _Model & FieldsOf<F>)}
 */
export const Model = /** @type {any} */ (_Model);

/**
 * The name of the model of a class: the one it declares or extends, or the
 * one of the class it derives from.
 *
 * @param {ModelClass} ModelClass
 * @returns {string}
 */
export function getModelName(ModelClass) {
    for (let cls = ModelClass; cls !== _Model; cls = Object.getPrototypeOf(cls)) {
        if (Object.hasOwn(cls, "_inherit")) {
            return cls._inherit;
        }
        if (Object.hasOwn(cls, "_name")) {
            return cls._name;
        }
    }
    return "";
}

/**
 * @param {ModelClass} ModelClass
 * @returns {boolean} whether a class of the chain declares the model
 */
function isDeclared(ModelClass) {
    for (let cls = ModelClass; cls !== _Model; cls = Object.getPrototypeOf(cls)) {
        if (Object.hasOwn(cls, "_name") && !Object.hasOwn(cls, "_inherit")) {
            return true;
        }
    }
    return false;
}

/**
 * A class declares or extends one model: it cannot derive from a class of
 * another one.
 *
 * @param {ModelClass} ModelClass
 */
function checkClass(ModelClass) {
    const name = getModelName(ModelClass);
    for (let cls = ModelClass; cls !== _Model; cls = Object.getPrototypeOf(cls)) {
        const names = [];
        if (Object.hasOwn(cls, "_inherit")) {
            names.push(cls._inherit);
        }
        if (Object.hasOwn(cls, "_name")) {
            names.push(cls._name);
        }
        const other = names.find((n) => n !== name);
        if (other !== undefined) {
            throw new Error(
                `Class "${ModelClass.name}" of model "${name}" cannot derive from a class of model "${other}"`
            );
        }
    }
}

/**
 * The class with an `_inherit` that `ModelClass` is or derives from, if any:
 * the link that gets rewired when extensions are chained.
 *
 * @param {ModelClass} ModelClass
 * @returns {ModelClass | null}
 */
function getExtensionRoot(ModelClass) {
    for (let cls = ModelClass; cls !== _Model; cls = Object.getPrototypeOf(cls)) {
        if (Object.hasOwn(cls, "_inherit")) {
            return cls;
        }
        if (Object.hasOwn(cls, "_name")) {
            return null;
        }
    }
    return null;
}

/**
 * Chains the classes of each model, like the Python registry does with
 * `_inherit`, and returns the final class of each model.
 *
 * Note: this rewires the prototype chains of the extension classes, which is
 * global. Two stores composing different sets of extensions for the same model
 * would see the last composition.
 *
 * @param {ModelClass[]} classes
 * @returns {Map<string, ModelClass>}
 */
export function composeClasses(classes) {
    /** @type {Map<string, ModelClass>} */
    const finalClasses = new Map();
    for (const ModelClass of classes) {
        const name = getModelName(ModelClass);
        if (!name) {
            throw new Error(
                `Class "${ModelClass.name}" has no model: give it a static _name, or an _inherit`
            );
        }
        checkClass(ModelClass);
        const previous = finalClasses.get(name);
        if (!previous) {
            finalClasses.set(name, ModelClass);
            continue;
        }
        if (previous === ModelClass || previous.prototype instanceof ModelClass) {
            // already part of the chain
            continue;
        }
        if (!(ModelClass.prototype instanceof previous)) {
            // insert the previous classes of the model below this extension
            const root = getExtensionRoot(ModelClass);
            if (!root) {
                throw new Error(
                    isDeclared(previous)
                        ? `Model "${name}" is declared twice`
                        : `Model "${name}" is extended before it is declared: list class "${ModelClass.name}" first`
                );
            }
            Object.setPrototypeOf(root.prototype, previous.prototype);
            Object.setPrototypeOf(root, previous);
        }
        finalClasses.set(name, ModelClass);
    }
    for (const [name, ModelClass] of finalClasses) {
        if (!isDeclared(ModelClass)) {
            throw new Error(
                `Model "${name}" is extended by class "${ModelClass.name}", but no class declares it`
            );
        }
    }
    return finalClasses;
}

/**
 * The fields declared along the class chain of a model, base class first.
 *
 * @param {ModelClass} ModelClass
 * @returns {Record<string, object>}
 */
export function getDeclaredFields(ModelClass) {
    const chain = [];
    for (let cls = ModelClass; cls !== _Model; cls = Object.getPrototypeOf(cls)) {
        if (!Object.hasOwn(cls, "fields")) {
            continue;
        }
        for (const [fieldName, declaration] of Object.entries(cls.fields)) {
            if (!declaration?.[FIELD]) {
                throw new Error(`"${getModelName(cls)}.${fieldName}" is not a field declaration`);
            }
        }
        chain.unshift(cls.fields);
    }
    return Object.assign({}, ...chain);
}

/**
 * The indexes declared along the class chain of a model.
 *
 * @param {ModelClass} ModelClass
 * @returns {string[]}
 */
export function getDeclaredIndexes(ModelClass) {
    const indexes = new Set();
    for (let cls = ModelClass; cls !== _Model; cls = Object.getPrototypeOf(cls)) {
        if (Object.hasOwn(cls, "_indexes")) {
            cls._indexes.forEach((fieldName) => indexes.add(fieldName));
        }
    }
    return [...indexes];
}
