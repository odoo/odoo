odoo.define('point_of_sale.ComponentsRegistry', function(require) {
    'use strict';

    // Object that maps `name` to the class implementation extended in-place.
    const includedMap = {};
    // Object that maps `name` to the array of callbacks to generate the extended class.
    const extendedCBMap = {};
    // Object that maps `name` extended class to the `name` of its super in the includedMap.
    const extendedSuperNameMap = {};
    // For faster access, we can `freeze` the registry so that instead of dynamically generating
    // the extended classes, it is taken from the cache instead.
    const cache = {};

    /**
     * **Usage:**
     * ```
     * class A {}
     * Registry.add('A', A);
     *
     * const AExt1 = A => class extends A {}
     * Registry.extend('A', AExt1)
     *
     * const B = A => class extends A {}
     * Registry.addByExtending('B', 'A', B)
     *
     * const AExt2 = A => class extends A {}
     * Registry.extend('A', AExt2)
     *
     * Registry.get('A')
     * // above returns: AExt2 -> AExt1 -> A
     * // Basically, 'A' in the registry points to
     * // the inheritance chain above.
     *
     * Registry.get('B')
     * // above returns: B -> AExt2 -> AExt1 -> A
     * // Even though B extends A before applying all
     * // the extensions of A, when getting it from the
     * // registry, the return points to a class with
     * // inheritance chain that includes all the extensions
     * // of 'A'.
     *
     * Registry.freeze()
     * // Example 'B' above is lazy. Basically, it is only
     * // computed when we call `get` from the registry.
     * // If we know that no more dynamic inheritances will happen,
     * // we can freeze the registry and cache the final form
     * // of each class in the registry.
     * ```
     */
    const Registry = {
        add(newClassName, Class) {
            includedMap[newClassName] = Class;
        },
        addByExtending(newClassName, classNameToExtend, using) {
            extendedCBMap[newClassName] = [using];
            extendedSuperNameMap[newClassName] = classNameToExtend;
        },
        extend(name, using) {
            if (includedMap[name]) {
                const toExtend = includedMap[name];
                const extended = using(toExtend);
                includedMap[name] = extended;
            } else if (extendedCBMap[name]) {
                extendedCBMap[name].push(using);
            } else if (using instanceof Function) {
                extendedCBMap[name] = [using];
            }
        },
        get(name) {
            if (this.isFrozen) return cache[name];
            if (!(includedMap[name] || extendedCBMap[name])) return undefined;
            return includedMap[name]
                ? includedMap[name]
                : extendedCBMap[name].reduce(
                      (acc, a) => a(acc),
                      includedMap[extendedSuperNameMap[name]]
                  );
        },
        freeze() {
            for (let [name, Class] of Object.entries(includedMap)) {
                cache[name] = Class;
            }
            for (let [name, extenders] of Object.entries(extendedCBMap)) {
                cache[name] = extenders.reduce(
                    (acc, extender) => extender(acc),
                    includedMap[extendedSuperNameMap[name]]
                );
            }
            this.isFrozen = true;
        },
    };

    return Registry;
});
