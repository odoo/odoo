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
    lazyComputed(object, lazyName, lazyMethod);
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

function defineLazyGetterTrap(Class) {
    const getters = getLazyGetters(Class);
    return function get(target, prop, receiver) {
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

function lazyComputed(obj, propName, compute) {
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
    effect(
        function recompute(obj) {
            const value = [];
            obj[key] = () => {
                if (!value.length) {
                    value.push(compute(obj));
                }
                return value[0];
            };
        },
        [obj]
    );
}

export class WithLazyGetterTrap {
    constructor({ traps = {} }) {
        const Class = this.constructor;
        const instance = new Proxy(this, { get: defineLazyGetterTrap(Class), ...traps });
        for (const [lazyName, func] of getLazyGetters(Class).values()) {
            lazyComputed(instance, lazyName, func);
        }
        return instance;
    }
}
