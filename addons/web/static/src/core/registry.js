import { EventBus, validate } from "@odoo/owl";

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------
export class KeyNotFoundError extends Error {}

export class DuplicatedKeyError extends Error {}

// -----------------------------------------------------------------------------
// Validation
// -----------------------------------------------------------------------------

const validateSchema = (value, schema) => {
    if (!odoo.debug) {
        return;
    }
    validate(value, schema);
}

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @template S
 * @template C
 * @typedef {import("registries").RegistryData<S, C>} RegistryData
 */

/**
 * @template T
 * @typedef {T extends RegistryData<any, any> ? T : RegistryData<T, {}>} ToRegistryData
 */

/**
 * @template T
 * @typedef {ToRegistryData<T>["__itemShape"]} GetRegistryItemShape
 */

/**
 * @template T
 * @typedef {ToRegistryData<T>["__categories"]} GetRegistryCategories
 */

/**
 * Registry
 *
 * The Registry class is basically just a mapping from a string key to an object.
 * It is really not much more than an object. It is however useful for the
 * following reasons:
 *
 * 1. it let us react and execute code when someone add something to the registry
 *   (for example, the FunctionRegistry subclass this for this purpose)
 * 2. it throws an error when the get operation fails
 * 3. it provides a chained API to add items to the registry.
 *
 * @template T
 */
export class Registry extends EventBus {
    /**
     * @param {string} [name]
     */
    constructor(name) {
        super();
        /** @type {Record<string, [number, GetRegistryItemShape<T>]>}*/
        this.content = {};
        /** @type {{ [P in keyof GetRegistryCategories<T>]?: Registry<GetRegistryCategories<T>[P]> }} */
        this.subRegistries = {};
        /** @type {GetRegistryItemShape<T>[]}*/
        this.elements = null;
        /** @type {[string, GetRegistryItemShape<T>][]}*/
        this.entries = null;
        this.name = name;
        this.validationSchema = null;

        this.addEventListener("UPDATE", () => {
            this.elements = null;
            this.entries = null;
        });
    }

    /**
     * Add an entry (key, value) to the registry if key is not already used. If
     * the parameter force is set to true, an entry with same key (if any) is replaced.
     *
     * Note that this also returns the registry, so another add method call can
     * be chained
     *
     * @param {string} key
     * @param {GetRegistryItemShape<T>} value
     * @param {{force?: boolean, sequence?: number}} [options]
     * @returns {Registry<T>}
     */
    add(key, value, { force, sequence } = {}) {
        if (this.validationSchema) {
            validateSchema(value, this.validationSchema);
        }
        if (!force && key in this.content) {
            throw new DuplicatedKeyError(
                `Cannot add key "${key}" in the "${this.name}" registry: it already exists`
            );
        }
        let previousSequence;
        if (force) {
            const elem = this.content[key];
            previousSequence = elem && elem[0];
        }
        sequence = sequence === undefined ? previousSequence || 50 : sequence;
        this.content[key] = [sequence, value];
        const payload = { operation: "add", key, value };
        this.trigger("UPDATE", payload);
        return this;
    }

    /**
     * Get an item from the registry
     *
     * @param {string} key
     * @returns {GetRegistryItemShape<T>}
     */
    get(key, defaultValue) {
        if (arguments.length < 2 && !(key in this.content)) {
            throw new KeyNotFoundError(`Cannot find key "${key}" in the "${this.name}" registry`);
        }
        const info = this.content[key];
        return info ? info[1] : defaultValue;
    }

    /**
     * Check the presence of a key in the registry
     *
     * @param {string} key
     * @returns {boolean}
     */
    contains(key) {
        return key in this.content;
    }

    /**
     * Get a list of all elements in the registry. Note that it is ordered
     * according to the sequence numbers.
     *
     * @returns {GetRegistryItemShape<T>[]}
     */
    getAll() {
        if (!this.elements) {
            const content = Object.values(this.content).sort((el1, el2) => el1[0] - el2[0]);
            this.elements = content.map((elem) => elem[1]);
        }
        return this.elements.slice();
    }

    /**
     * Return a list of all entries, ordered by sequence numbers.
     *
     * @returns {[string, GetRegistryItemShape<T>][]}
     */
    getEntries() {
        if (!this.entries) {
            const entries = Object.entries(this.content).sort((el1, el2) => el1[1][0] - el2[1][0]);
            this.entries = entries.map(([str, elem]) => [str, elem[1]]);
        }
        return this.entries.slice();
    }

    /**
     * Remove an item from the registry
     *
     * @param {string} key
     */
    remove(key) {
        const value = this.content[key];
        delete this.content[key];
        const payload = { operation: "delete", key, value };
        this.trigger("UPDATE", payload);
    }

    /**
     * Open a sub registry (and create it if necessary)
     *
     * @template {keyof GetRegistryCategories<T> & string} K
     * @param {K} subcategory
     * @returns {Registry<GetRegistryCategories<T>[K]>}
     */
    category(subcategory) {
        if (!(subcategory in this.subRegistries)) {
            this.subRegistries[subcategory] = new Registry(subcategory);
        }
        return this.subRegistries[subcategory];
    }

    addValidation(schema) {
        if (this.validationSchema) {
            throw new Error("Validation schema already set on this registry");
        }
        this.validationSchema = schema;
        for (const value of this.getAll()) {
            validateSchema(value, schema);
        }
    }
}

/** @type {Registry<import("registries").GlobalRegistry>} */
export const registry = new Registry();
