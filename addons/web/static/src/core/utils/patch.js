/**
@typedef {{
    originalProperties: Map<string | symbol, PropertyDescriptor>;
    skeleton: object;
    extensions: Map<object, Map<string | symbol, PropertyDescriptor>>;
}} PatchDescription
*/

/**
@typedef {new (...args: any[]) => any} AnyCtor
*/

/**
@template T
@template U
@typedef {Partial<T> & U & ThisType<T & U>} Extension
*/

/** @type {WeakMap<object, PatchDescription>} */
const patchDescriptions = new WeakMap();

/**
 * Create or get the patch description for the given `objToPatch`.
 * @param {object} objToPatch
 * @returns {PatchDescription}
 */
function getPatchDescription(objToPatch) {
    if (!patchDescriptions.has(objToPatch)) {
        patchDescriptions.set(objToPatch, {
            originalProperties: new Map(),
            skeleton: Object.create(Object.getPrototypeOf(objToPatch)),
            extensions: new Map(),
        });
    }
    return patchDescriptions.get(objToPatch);
}

/**
 * @param {object} objToPatch
 * @returns {boolean}
 */
function isClassPrototype(objToPatch) {
    // class A {}
    // isClassPrototype(A) === false
    // isClassPrototype(A.prototype) === true
    // isClassPrototype(new A()) === false
    // isClassPrototype({}) === false
    return (
        Reflect.has(objToPatch, "constructor") && objToPatch.constructor?.prototype === objToPatch
    );
}

/**
 * @param {object} obj
 * @param {string | symbol} key
 * @returns {boolean}
 */
function isPropUserDefined(obj, key) {
    const property = Reflect.getOwnPropertyDescriptor(obj, key);
    return !!property && (!!property.get || property.writable);
};

/**
 * Traverse the prototype chain to find a potential property.
 * @param {object} objToPatch
 * @param {string | symbol} key
 * @returns {object}
 */
function findAncestorPropertyDescriptor(objToPatch, key) {
    let descriptor = null;
    let prototype = objToPatch;
    do {
        descriptor = Object.getOwnPropertyDescriptor(prototype, key);
        prototype = Object.getPrototypeOf(prototype);
    } while (!descriptor && prototype);
    return descriptor;
}

/**
 * Get all name and symbol properties of `obj`.
 * @param {object} obj
 * @returns {Map<string | symbol, PropertyDescriptor>}
 */
function getPropertyMap(obj) {
    const keys = Reflect.ownKeys(obj);
    return new Map(keys.map((key) => [key, Reflect.getOwnPropertyDescriptor(obj, key)]));
}

/**
 * Overrides the properties on the object to patch.
 * @param {object} objToPatch
 * @param {object} extension
 * @param {Map<string | symbol, PropertyDescriptor>} properties
 */
function applyPatch(objToPatch, extension, properties) {
    const description = getPatchDescription(objToPatch);
    description.extensions.set(extension, properties);

    for (const [key, newProperty] of properties) {
        const oldProperty = Reflect.getOwnPropertyDescriptor(objToPatch, key);

        if (oldProperty) {
            // Store the old property on the skeleton.
            Reflect.defineProperty(description.skeleton, key, oldProperty);
        }

        if (!description.originalProperties.has(key)) {
            // Keep a trace of original property (prop before first patch), useful for unpatching.
            description.originalProperties.set(key, oldProperty);
        }

        if ((newProperty.get && 1) ^ (newProperty.set && 1)) {
            // get and set are defined together. If they are both defined
            // in the previous descriptor but only one in the new descriptor
            // then the other will be undefined so we need to apply the
            // previous descriptor in the new one.
            const ancestorProperty = findAncestorPropertyDescriptor(objToPatch, key);
            newProperty.get = newProperty.get ?? ancestorProperty?.get;
            newProperty.set = newProperty.set ?? ancestorProperty?.set;
        }

        // Replace the old property by the new one.
        Reflect.defineProperty(objToPatch, key, newProperty);
    }

    // Sets the current skeleton as the extension's prototype to make
    // `super` keyword working and then set extension as the new skeleton.
    description.skeleton = Object.setPrototypeOf(extension, description.skeleton);
}

/**
 * Reset the original state of the object to unpatch, remove the path and reapply the other patches.
 * @param {object} objToUnpatch
 * @param {object} extension
 */
function removePatch(objToUnpatch, extension) {
    const description = getPatchDescription(objToUnpatch);
    // Remove the description to start with a fresh base.
    patchDescriptions.delete(objToUnpatch);

    for (const [key, property] of description.originalProperties) {
        if (property) {
            // Restore the original property on the `objToUnpatch` object.
            Object.defineProperty(objToUnpatch, key, property);
        } else {
            // Or remove the property if it did not exist at first.
            delete objToUnpatch[key];
        }
    }

    // Re-apply the patches without the current one.
    description.extensions.delete(extension);
    for (const [extension, properties] of description.extensions) {
        applyPatch(objToUnpatch, extension, properties);
    }
}

/**
 * Patch an object with the object initializer notation.
 * @template T
 * @template {object} U
 * @param {T} objToPatch The object to patch
 * @param {Extension<T, U>} extension The object containing the patched properties
 */
function patchObject(objToPatch, extension) {
    const properties = getPropertyMap(extension);
    if (isClassPrototype(objToPatch)) {
        // A property is enumerable on object literals ({ prop: 1 }) but not on classes (class A {}).
        // Here, we only check if we patch a class prototype.
        for (const property of properties.values()) {
            property.enumerable = false;
        }
    }

    applyPatch(objToPatch, extension, properties);
    return () => {
        removePatch(objToPatch, extension);
    };
}

/**
 * Patch a class with the class notation.
 * @param {AnyCtor} ctor
 */
function patchClass(ctor) {
    const prototype = ctor.prototype;
    const prototypeProps = getPropertyMap(prototype);
    // Do not override "constructor" property.
    prototypeProps.delete("constructor");
    const basePrototype = Reflect.getPrototypeOf(prototype);
    applyPatch(basePrototype, prototype, prototypeProps);

    const constructorProps = getPropertyMap(ctor);
    // Do not override "prototype" property.
    constructorProps.delete("prototype");
    if (!isPropUserDefined(ctor, "name")) {
        // Override the "name" property only if it is set.
        constructorProps.delete("name");
    }
    if (!isPropUserDefined(ctor, "length")) {
        // Override the "length" property only if it is set.
        constructorProps.delete("length");
    }
    const baseConstructor = Reflect.getPrototypeOf(ctor);
    applyPatch(baseConstructor, ctor, constructorProps);

    return () => {
        removePatch(baseConstructor, ctor);
        removePatch(basePrototype, prototype);
    };
}

/**
 * ## Patch an object with the object initializer notation.
 *
 * If the intent is to patch a class, don't forget to patch the prototype, unless
 * you want to patch static properties/methods.
 *
 * ```
 * // patch an object.
 * patch(obj, {
 *     exec() {
 *         super.exec();
 *         // Do something more.
 *     },
 * });
 *
 * // patch the static properties of a class.
 * patch(OriginalClass, {
 *     staticMethod() {
 *         super.staticMethod();
 *         // Do something more.
 *     }
 * });
 * // patch the properties of a class instance.
 * patch(OriginalClass.prototype, {
 *     instanceMethod() {
 *         super.instanceMethod();
 *         // Do something more.
 *     }
 * });
 * ```
 *
 * @template T
 * @overload
 * @param {T} objToPatch The object to patch
 * @returns {() => void} Returns an unpatch function
 */
/**
 * ## Patch a class with the class notation.
 *
 * ```
 * patch(class Patch extends Original {
 *     setup() {
 *         super.setup();
 *         // Do something more.
 *     }
 * });
 * ```
 *
 * @template T
 * @template {object} U
 * @overload
 * @param {T} objToPatch The object to patch
 * @param {Extension<T, U>} extension The object containing the patched properties
 * @returns {() => void} Returns an unpatch function
 */
export function patch(objToPatch, extension) {
    if (extension) {
        return patchObject(objToPatch, extension);
    } else {
        return patchClass(objToPatch);
    }
}
