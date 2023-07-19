/** @odoo-module */

import { reactive } from "@odoo/owl";

/**
 * This class should be used as a base when creating a class that is intended to
 * be used within the reactivity system, it avoids a specific class of bug where
 * callbacks that capture `this` declared in the constructor would escape the
 * reactivity system and prevent the observers from being notified:
 *
 * const bus = new EventBus();
 * class MyClass {
 *   constructor() {
 *     this.counter = 0;
 *     bus.addEventListener("change", () => this.counter++);
 *     //                                   ^ Will never be reactive, this mutation will be missed
 *   }
 * }
 * const myObj = reactive(new MyClass(bus), () => console.log(myObj.counter));
 * myObj.counter++; // logs 0;
 * bus.trigger("change"); // logs nothing!
 * myObj.counter++; // logs 2. counter == 1 was missed.
 */
export class Reactive {
    constructor() {
        return reactive(this);
    }
}

/**
 * Creates a side-effect that runs based on the content of reactive objects.
 *
 * @template {object[]} T
 * @param {(...args: [...T]) => X} cb callback for the effect
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
