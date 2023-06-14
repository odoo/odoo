/** @odoo-module */

import { reactive } from "@odoo/owl";

export class Reactive {
    constructor() {
        return reactive(this);
    }
}

/**
 * Creates a side-effect that runs based on the content of reactive objects.
 *
 * @template {object[]} T
 * @param {(...args: [...T]) => void} cb callback for the effect
 * @param {[...T]} deps the reactive objects that the effect depends on
 */
export function effect(cb, deps) {
    const reactiveDeps = reactive(deps, () => {
        cb(...reactiveDeps);
    });
    cb(...reactiveDeps);
}

/**
 * Adds computed properties to a reactive object derived from multiples sources.
 *
 * @template {object} T
 * @template {object[]} U
 * @template {{[key: string]: (this: T, ...rest: [...U]) => unknown}} V
 * @param {T} obj the reactive object on which to add the computed
 * properties
 * @param {[...U]} sources the reactive objects which are needed to compute
 * the properties
 * @param {V} descriptor the object containing methods to compute the
 * properties
 * @returns {T & {[key in keyof V]: ReturnType<V[key]>}}
 */
export function withComputedProperties(obj, sources, descriptor) {
    for (const [key, compute] of Object.entries(descriptor)) {
        effect(
            (obj, sources) => {
                obj[key] = compute.call(obj, ...sources);
            },
            [obj, sources]
        );
    }
    return obj;
}
