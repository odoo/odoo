import { derived } from "@odoo/owl";

const mapObjectToKeyToDerived = new Map();
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
    let keys = mapObjectToKeyToDerived.get(object);
    if (!keys) {
        keys = new Map();
        mapObjectToKeyToDerived.set(object, keys);
    }
    let d = keys.get(name);
    if (!d) {
        d = derived(() => func.call(object), { name: `lazyGetter(${name})` });
        keys.set(name, d);
    }

    Object.defineProperty(object, name, { get: d });
}

export class WithLazyGetterTrap {
    constructor({ traps = {} }) {
        return new Proxy(this, { get: defineLazyGetterTrap(this), ...traps });
    }
}
function defineLazyGetterTrap(object) {
    const getters = getAllDeriveds(object);

    return function get(target, prop, receiver) {
        if (!getters.has(prop)) {
            return Reflect.get(target, prop, receiver);
        }
        // For a getter, we should get the value from the receiver.
        // Because the receiver is linked to the reactivity.
        // We want to read the getter from it to make sure that the getter
        // is part of the reactivity as well.
        // To avoid infinite recursion, we disable this proxy trap
        // during the time the lazy getter is accessed.
        return getters.get(prop)(receiver);
    };
}
function getAllDeriveds(obj) {
    const deriveds = new Map();
    while (obj !== null) {
        const descriptors = Object.getOwnPropertyDescriptors(obj);
        for (const [name, descriptor] of Object.entries(descriptors)) {
            if (
                !descriptor.get ||
                deriveds.has(name) ||
                (name.startsWith("__") && name.endsWith("__"))
            ) {
                continue;
            }
            const d = derived(() => descriptor.get.call(obj), { name: `lazyGetter(${name})` });
            deriveds.set(name, (currentObj) => {
                obj = currentObj;
                return d();
            });
        }
        obj = Object.getPrototypeOf(obj);
    }
    return deriveds;
}
