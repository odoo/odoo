import { effect } from "@web/core/utils/reactive";
import { getDisabler } from "./proxy_trap";

function getAllGetters(proto) {
    const getterNames = new Set();
    const getters = new Set();
    while (proto !== null) {
        const descriptors = Object.getOwnPropertyDescriptors(proto);
        for (const [name, descriptor] of Object.entries(descriptors)) {
            if (descriptor.get && !getterNames.has(name)) {
                getterNames.add(name);
                getters.add([name, descriptor.get]);
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

function getGetters(Class) {
    if (!classGetters.has(Class)) {
        const getters = new Map();
        for (const [name, func] of getAllGetters(Class.prototype)) {
            if (name.startsWith("__") && name.endsWith("__")) {
                continue;
            }
            getters.set(name, [`__lazy_${name}`, (obj) => func.call(obj)]);
        }
        classGetters.set(Class, getters);
    }
    return classGetters.get(Class);
}

function defineLazyGetterTrap(Class) {
    const getters = getGetters(Class);
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
    constructor({ traps }) {
        const Class = this.constructor;
        const instance = new Proxy(this, { get: defineLazyGetterTrap(Class), ...traps });
        for (const [lazyName, func] of getGetters(Class).values()) {
            lazyComputed(instance, lazyName, func);
        }
        return instance;
    }
}
