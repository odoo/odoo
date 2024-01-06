/** @odoo-module */

import { effect } from "@web/core/utils/reactive";

function lazyComputed(obj, propName, compute) {
    const key = Symbol(propName);
    Object.defineProperty(obj, propName, {
        get() {
            return this[key]();
        },
        configurable: true,
    });

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

export function createModelWithLazyGetters(Class) {
    const getters = new Map();
    for (const [name, func] of getAllGetters(Class.prototype)) {
        if (name.startsWith("__") && name.endsWith("__")) {
            continue;
        }
        const lazyName = `__lazy_${name}`;
        getters.set(name, [lazyName, (obj) => func.call(obj)]);
    }
    class WithLazyGetters extends Class {
        constructor(...args) {
            super(...args);
            for (const [lazyName, func] of getters.values()) {
                lazyComputed(this, lazyName, func);
            }
        }
        get(getterName) {
            const [lazyName] = getters.get(getterName);
            if (lazyName) {
                return this[lazyName];
            } else {
                throw new Error(`Getter ${getterName} is not defined.`);
            }
        }
    }
    return WithLazyGetters;
}
