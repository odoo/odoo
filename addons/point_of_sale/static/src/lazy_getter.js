import { effect } from "@web/core/utils/reactive";
import { getDisabler } from "./proxy_trap";

function getAllGetters(proto) {
    const getters = new Map();
    while (proto !== null) {
        const descriptors = Object.getOwnPropertyDescriptors(proto);
        for (const [name, descriptor] of Object.entries(descriptors)) {
            if (descriptor.get && !getters.has(name)) {
                getters.set(name, descriptor.get);
            }
        }
        proto = Object.getPrototypeOf(proto);
    }
    return getters;
}

const classGetters = new Map();

export function clearGettersCache() {
    classGetters.clear();
}

function getLazyGetters(Class) {
    if (!classGetters.has(Class)) {
        const getters = new Map();
        const excludedLazyGetters = Class.excludedLazyGetters || [];
        for (const [name, func] of getAllGetters(Class.prototype)) {
            if (
                (name.startsWith("__") && name.endsWith("__")) ||
                excludedLazyGetters.includes(name)
            ) {
                continue;
            }
            getters.set(name, _defineLazyGetter(name, func));
        }
        classGetters.set(Class, getters);
        // for (const [lazyName, func] of getters.values()) {
        // attachLazyComputed(instance, lazyName, func);
        // }
    }
    return classGetters.get(Class);
}

function _defineLazyGetter(name, func) {
    return [`__lazy_${name}`, (obj) => func.call(obj)];
}

/**
 /**
 * Creates a lazy getter for an object instance, ensuring the value is (re)computed only when needed.
 * @param {Object} object - The object on which to define the lazy getter.
 * @param {string} name - The name of the getter
 * @param {Function} func - The function that computes the property value when needed.
 */
export function createLazyGetter(object, name, func) {
    if (!(object instanceof WithLazyGetterTrap)) {
        throw new Error("The object must be an instance of WithLazyGetterTrap");
    }
    const [lazyName, lazyMethod] = _defineLazyGetter(name, func);
    attachLazyComputed(object, lazyName, lazyMethod);
    const getter = function () {
        const disabler = getDisabler(object, name);
        if (disabler.isDisabled()) {
            return func();
        }
        return object[lazyName];
    };
    Object.defineProperty(object, name, {
        get: function () {
            return getter();
        },
    });
}

const targetKeyGetters = new WeakMap();

function defineLazyGetterTrap(Class) {
    // const getters = getLazyGetters(Class);
    return function get(target, prop, receiver) {
        const keysToGetters = targetKeyGetters.get(target);
        const getters = keysToGetters?.get(prop);
        const getter = getters?.get(prop);
        if (!getter) {
            return Reflect.get(target, prop, receiver);
        }

        const disabler = getDisabler(target, prop);
        if (disabler.isDisabled() || !getters.has(prop)) {
            return Reflect.get(target, prop, receiver);
        }
        return disabler.call(() => {
            const [lazyName] = getters.get(prop);
            // For a getter, we should get the value from the receiver.
            // Because the receiver is linked to the reactivity.
            // We want to read the getter from it to make sure that the getter
            // is part of the reactivity as well.
            // To avoid infinite recursion, we disable this proxy trap
            // during the time the lazy getter is accessed.
            return receiver[lazyName];
        });
    };
}

function attachLazyComputed(obj, propName, compute) {
    const key = Symbol(propName);
    Object.defineProperty(obj, propName, {
        get() {
            return this[key]();
        },
        configurable: true,
    });

    /**
     * - `recompute` depends on the dependencies of `compute`.
     * - When one of the dependencies of `compute` changed, `recompute` invalidates the cache of the `compute`.
     * - The cache of `compute` is saved in `value`.
     */
    effect(function recompute() {
        const cache = {};
        obj[key] = () => {
            if (!("value" in cache)) {
                cache.value = compute(obj);
            }
            return cache.value;
        };
    });
}

export class WithLazyGetterTrap {
    constructor({ traps = {} }) {
        const Class = this.constructor;
        const instance = new Proxy(this, { get: defineLazyGetterTrap(Class), ...traps });
        return instance;
    }
}

// const pos = reactive({}, (change) => {
//     console.log(changes);
// });

// let first = true;
// effect(() => {
//     pos.x; // track
//     if (!first) {
//         addChange(pos, "x");
//     }
//     first = false;
// });

// export function computedField(compute) {
//     let lastFn = () => {
//         let result;
//         let computed = false;
//         effect(() => {
//             const obj = {};
//             lastFn = () => {
//                 if (!("value" in obj)) {
//                     obj.value = compute();
//                 }
//                 return obj.value;
//             };
//             result = !computed && lastFn();
//             computed = true;
//         });
//         return result;
//     };
//     return () => lastFn();
// }
export function computedField(compute) {
    let lastFn = () => {
        let result;
        effect(() => {
            const obj = {};
            lastFn = () => {
                if (!("value" in obj)) {
                    obj.value = compute();
                }
                return obj.value;
            };
            result = lastFn();
        });
        return result;
    };
    return () => lastFn();
}

// const r = reactive({ value: "test" });

class A extends WithLazyGetterTrap {
    x = 1;
    get f1() {
        console.log("compute f1", this.x);
    }
    get f2() {
        console.log("compute f2", this.x);
    }
}
class B extends WithLazyGetterTrap {
    x = 1;
    get f3() {
        console.log("compute f3", this.x);
    }
    get f4() {
        console.log("compute f4", this.x);
    }
}

const fn = () => {
    const a1 = new A();
    const a2 = new A();
    const b1 = new B();
    const b2 = new B();

    a1.f1();
    a1.x++;
};
fn();

const reactive1 = reactive({ value: 1 });
const derived1 = derived(() => reactive1.value + 100);

derived1();
