/** @odoo-module **/

import { EventBus } from "@odoo/owl";

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------
export class KeyNotFoundError extends Error {}

export class DuplicatedKeyError extends Error {}

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
 * @template [K=string] keys type
 * @template [V=any] values type
 */
export class Registry extends EventBus {
    /**
     * @param {string} [name]
     */
    constructor(name) {
        super();
        this.content = {};
        this.subRegistries = {};
        this.elements = null;
        this.entries = null;
        this.name = name;

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
     * @param {K} key
     * @param {V} value
     * @param {{ force?: boolean; sequence?: number }} [options]
     * @returns {Registry<K, V>}
     */
    add(key, value, { force, sequence } = {}) {
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
     * @param {K} key
     * @returns {V}
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
     * @param {K} key
     * @returns {boolean}
     */
    contains(key) {
        return key in this.content;
    }

    /**
     * Get a list of all elements in the registry. Note that it is ordered
     * according to the sequence numbers.
     *
     * @returns {V[]}
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
     * @returns {[K, V][]}
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
     * @param {K} key
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
     * @template [SK=string]
     * @template [SV=any]
     * @param {string} subcategory
     * @returns {Registry<SK, SV>}
     */
    category(subcategory) {
        if (!(subcategory in this.subRegistries)) {
            this.subRegistries[subcategory] = new Registry(subcategory);
        }
        return this.subRegistries[subcategory];
    }
}

export const registry = new Registry();
