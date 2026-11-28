import { computed } from "@odoo/owl";

const mapObjectToKeyToDerived = new Map();
let classGetters = new WeakMap();

export function clearGettersCache() {
    classGetters = new WeakMap();
}

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
        d = computed(() => func.call(object), { name: `lazyGetter(${name})` });
        keys.set(name, d);
    }

    Object.defineProperty(object, name, { get: d });
}

export class WithLazyGetterTrap {
    constructor({ traps = {} }) {
        const Class = this.constructor;
        if (Class.enableLazyGetters === false) {
            return;
        }
        return new Proxy(this, { get: defineLazyGetterTrap(Class), ...traps });
    }
}

function defineLazyGetterTrap(Class) {
    const getterNames = getGetterNames(Class);
    let deriveds = null;

    return function get(target, prop, receiver) {
        if (!getterNames.has(prop)) {
            return Reflect.get(target, prop, receiver);
        }
        // For a getter, we should get the value from the receiver.
        // Because the receiver is linked to the reactivity.
        // We want to read the getter from it to make sure that the getter
        // is part of the reactivity as well.
        if (!deriveds) {
            deriveds = new Map();
        }
        let entry = deriveds.get(prop);
        if (!entry) {
            entry = {
                receiver,
                derived: computed(() => Reflect.get(target, prop, entry.receiver), {
                    name: `lazyGetter(${prop})`,
                }),
            };
            deriveds.set(prop, entry);
        } else {
            entry.receiver = receiver;
        }
        return entry.derived();
    };
}

function getGetterNames(Class) {
    let getterNames = classGetters.get(Class);
    if (!getterNames) {
        getterNames = new Set();
        let proto = Class.prototype;
        while (proto !== null) {
            const descriptors = Object.getOwnPropertyDescriptors(proto);
            for (const [name, descriptor] of Object.entries(descriptors)) {
                if (descriptor.get && !(name.startsWith("__") && name.endsWith("__"))) {
                    getterNames.add(name);
                }
            }
            proto = Object.getPrototypeOf(proto);
        }
        classGetters.set(Class, getterNames);
    }
    return getterNames;
}
