import { FIELD } from "./fields";

// Record slots. Symbols keep them out of the way of field names, which live on
// the prototype as accessors.
export const MODEL = Symbol("model"); // on the per-store prototype: the model meta
export const ID = Symbol("id");
export const OWNER = Symbol("owner"); // the store or draft the record belongs to
export const VALUES = Symbol("values"); // last server values, by field index; undefined = not loaded
export const CHANGES = Symbol("changes"); // null | Map<fieldIndex, { value, version }>
export const ATOMS = Symbol("atoms"); // signals, created on first read
export const FLAGS = Symbol("flags");
export const PARENT = Symbol("parent"); // forks only: the record this one overlays

export const NEW = 1; // created locally, not saved yet
export const DELETED = 2;
export const STUB = 4; // referenced by id, nothing loaded yet

/**
 * Base class of all store records.
 *
 * Records are built with `Object.create`, so constructors and class field
 * initializers never run for them: class fields are only read once, as field
 * declarations. Per-record initialization goes in `setup()`.
 *
 * A model is declared by a class with a static `_name`. Other addons extend it
 * with a class that has a static `_inherit` naming the same model: all such
 * classes are chained in registration order, and `super` follows the chain.
 */
export class Model {
    /** @type {string} name of the model, for a base class */
    static _name = "";
    /** @type {string} name of the extended model, for an extension class */
    static _inherit = "";
    /** local writes are tracked as changes (baseline + changes + versions) */
    static _tracked = false;
    /** @type {"field" | "record" | "model" | "none"} */
    static _reactivity = "field";
    /** @type {string[]} fields with a unique index, see `store.getBy` */
    static _indexes = [];

    /** @returns {number | string} */
    get id() {
        return this[ID];
    }

    /**
     * Called once when the record object is created in a store (created,
     * loaded or referenced), never for draft forks.
     */
    setup() {}
}

/**
 * @param {typeof Model} ModelClass
 */
function getModelName(ModelClass) {
    return Object.hasOwn(ModelClass, "_inherit") && ModelClass._inherit
        ? ModelClass._inherit
        : ModelClass._name;
}

/**
 * Chains the classes declaring the same model, like the Python registry does
 * with `_inherit`, and returns the final class of each model.
 *
 * Note: this rewires the prototype chains of the given classes, which is
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
        const name = getModelName(ModelClass);
        if (!name) {
            throw new Error(`Model class "${ModelClass.name}" has no _name or _inherit`);
        }
        const isExtension = Object.hasOwn(ModelClass, "_inherit");
        const previous = finalClasses.get(name);
        if (isExtension && !previous) {
            throw new Error(`Cannot extend model "${name}": its base class is not registered`);
        }
        if (!isExtension && previous) {
            throw new Error(`Model "${name}" is declared twice`);
        }
        if (previous && Object.getPrototypeOf(ModelClass) !== previous) {
            Object.setPrototypeOf(ModelClass.prototype, previous.prototype);
            Object.setPrototypeOf(ModelClass, previous);
        }
        finalClasses.set(name, ModelClass);
    }
    return finalClasses;
}

/**
 * Reads the fields declared as class fields along the class chain, by building
 * one raw instance.
 *
 * @param {typeof Model} ModelClass
 * @returns {Record<string, object>}
 */
export function getDeclaredFields(ModelClass) {
    const instance = new ModelClass();
    /** @type {Record<string, object>} */
    const declared = {};
    for (const [name, value] of Object.entries(instance)) {
        if (!value?.[FIELD]) {
            throw new Error(
                `Class field "${name}" of model "${getModelName(
                    ModelClass
                )}" is not a field declaration: per-record state belongs in setup()`
            );
        }
        declared[name] = value;
    }
    return declared;
}
