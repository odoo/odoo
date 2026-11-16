import { FIELD } from "./fields";

/**
 * @template T
 * @template [W=T]
 * @typedef {import("./fields").FieldSignal<T, W>} FieldSignal
 */

/**
 * A record class whose records are of type `I`: what `extend` returns. It is
 * spelled out, rather than derived from `typeof Model`, so that two models
 * that reference each other are not circular for TypeScript.
 *
 * @template I
 * @typedef {{
 *  new (...args: any[]): I;
 *  prototype: I;
 *  _name: string;
 *  _fields: Record<string, object>;
 *  _extension: boolean;
 *  _editable: boolean;
 *  _reactivity: "field" | "model";
 *  _indexes: string[];
 *  extend<C extends ModelClass<any>, F extends Record<string, any> = {}>(
 *      this: C,
 *      params?: { name?: string; fields?: F }
 *  ): ModelClass<InstanceType<C> & F>;
 * }} ModelClass
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

/**
 * Base class of all store records.
 *
 * A model is declared with `Model.extend({ name, fields })`, which returns the
 * record class of that model. It can be used as is, or subclassed to add
 * per-record state and methods:
 *
 *     class Partner extends Model.extend({
 *         name: "res.partner",
 *         fields: { name: fields.Char() },
 *     }) {
 *         label = computed(() => `[${this.id}] ${this.name()}`);
 *     }
 *
 * Fields are read by calling them and written with `set`: `partner.name()`,
 * `partner.name.set("Bob")`. `partner.name` is a stable per-record function,
 * so it can be passed around like a signal (e.g. to `t-model`).
 *
 * Another addon adds fields to a model by calling `extend` on its class,
 * without a name: `class MailPartner extends Partner.extend({ fields })`. All
 * the classes of a model are chained in registration order, like the Python
 * registry does with `_inherit`, and `super` follows the chain.
 *
 * Records are built by a store, never with `new` in application code. Class
 * fields run when the record is built, before its values are set: code that
 * needs the values right away goes in `setup()`.
 */
export class Model {
    /** @type {string} name of the model, set by `extend` */
    static _name = "";
    /** @type {Record<string, object>} own on each class returned by `extend` */
    static _fields = {};
    /** own and true on a class returned by `extend` without a name */
    static _extension = false;
    /**
     * Records are edited locally and saved back: a local write is kept as a
     * change, apart from the last server value. That is what `isDirty`,
     * `discard`, `ack` and `toCommands` work on. When false, a write replaces
     * the value: for data the client only mirrors.
     */
    static _editable = false;
    /**
     * How reads subscribe: to each field of each record, or to the whole model
     * (one subscription for all records, for large read-mostly data).
     *
     * @type {"field" | "model"}
     */
    static _reactivity = "field";
    /** @type {string[]} fields with a unique index, see `store.getBy` */
    static _indexes = [];

    /**
     * With a name, declares a model and returns its record class. Without one,
     * returns a class that adds fields to the model of this class.
     *
     * The fields of the returned class are typed from `fields`. A relational
     * field has to be cast to the field signal of its comodel class: see the
     * example in `fields.js`.
     *
     * `F` is not constrained to field signals on purpose: checking the
     * constraint would resolve the comodel classes, which is circular when two
     * models reference each other. Declarations are checked at runtime.
     *
     * @template {ModelClass<any>} C
     * @template {Record<string, any>} [F={}]
     * @this {C}
     * @param {{ name?: string; fields?: F }} [params]
     * @returns {ModelClass<InstanceType<C> & F>}
     */
    static extend({ name, fields } = {}) {
        if (name && this._name) {
            throw new Error(
                `Cannot declare model "${name}" from a class of model "${this._name}": omit the name to add fields to "${this._name}"`
            );
        }
        if (!name && !this._name) {
            throw new Error(`Model.extend() needs the name of the model to declare`);
        }
        const modelName = name || this._name;
        for (const [fieldName, declaration] of Object.entries(fields || {})) {
            if (!(/** @type {any} */ (declaration)?.[FIELD])) {
                throw new Error(`"${modelName}.${fieldName}" is not a field declaration`);
            }
        }
        const Base = /** @type {typeof Model} */ (this);
        const Extended = class extends Base {};
        Object.defineProperty(Extended, "name", { value: modelName });
        Extended._fields = /** @type {Record<string, object>} */ (fields || {});
        if (name) {
            Extended._name = name;
            Extended._extension = false;
        } else {
            Extended._extension = true;
        }
        return /** @type {any} */ (Extended);
    }

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
                `Records are built by a store: use store.create() or store.load(), not new ${this.constructor.name}()`
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
 * The class returned by `extend` without a name that `ModelClass` derives
 * from, if any: the link that gets rewired when extensions are chained.
 *
 * @param {typeof Model} ModelClass
 * @returns {typeof Model | null}
 */
function getExtensionRoot(ModelClass) {
    for (let cls = ModelClass; cls !== Model; cls = Object.getPrototypeOf(cls)) {
        if (Object.hasOwn(cls, "_extension")) {
            return cls._extension ? cls : null;
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
 * @param {(typeof Model)[]} classes
 * @returns {Map<string, typeof Model>}
 */
export function composeClasses(classes) {
    /** @type {Map<string, typeof Model>} */
    const finalClasses = new Map();
    for (const ModelClass of classes) {
        const name = ModelClass._name;
        if (!name) {
            throw new Error(
                `Class "${ModelClass.name}" has no model: declare one with Model.extend({ name, fields })`
            );
        }
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
                throw new Error(`Model "${name}" is declared twice`);
            }
            Object.setPrototypeOf(root.prototype, previous.prototype);
            Object.setPrototypeOf(root, previous);
        }
        finalClasses.set(name, ModelClass);
    }
    return finalClasses;
}

/**
 * The fields declared along the class chain of a model, base class first.
 *
 * @param {typeof Model} ModelClass
 * @returns {Record<string, object>}
 */
export function getDeclaredFields(ModelClass) {
    const chain = [];
    for (let cls = ModelClass; cls !== Model; cls = Object.getPrototypeOf(cls)) {
        if (Object.hasOwn(cls, "_fields")) {
            chain.unshift(cls._fields);
        }
    }
    return Object.assign({}, ...chain);
}
