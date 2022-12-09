/** @odoo-module */

/**
 * **Usage:**
 * ```
 * const Registry = new ClassRegistry();
 *
 * class A {}
 * Registry.add(A);
 *
 * const AExt1 = A => class extends A {}
 * Registry.extend(A, AExt1)
 *
 * const B = A => class extends A {}
 * Registry.addByExtending(B, A)
 *
 * const AExt2 = A => class extends A {}
 * Registry.extend(A, AExt2)
 *
 * Registry.get(A)
 * // above returns: AExt2 -> AExt1 -> A
 * // Basically, 'A' in the registry points to
 * // the inheritance chain above.
 *
 * Registry.get(B)
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
 *
 * IMPROVEMENT:
 * * So far, mixin can be accomplished by creating a method
 *  the takes a class and returns a class expression. This is then
 *  used before the extends keyword like so:
 *
 *  ```js
 *  class A {}
 *  Registry.add(A)
 *  const Mixin = x => class extends x {}
 *  //                          apply mixin
 *  //                              |
 *  //                              v
 *  const B = x => class extends Mixin(x) {}
 *  Registry.addByExtending(B, A)
 *  ```
 *
 *  In the example, `|B| => B -> Mixin -> A`, and this is pretty convenient
 *  already. However, this can still be improved since classes are only
 *  compiled after `Registry.freeze()`. Perhaps, we can make the
 *  Mixins extensible as well, such as so:
 *
 *  ```
 *  class A {}
 *  Registry.add(A)
 *  const Mixin = x => class extends x {}
 *  Registry.add(Mixin)
 *  const OtherMixin = x => class extends x {}
 *  Registry.add(OtherMixin)
 *  const B = x => class extends x {}
 *  Registry.addByExtending(B, A, [Mixin, OtherMixin])
 *  const ExtendMixin = x => class extends x {}
 *  Registry.extend(Mixin, ExtendMixin)
 *  ```
 *
 *  In the above, after `Registry.freeze()`,
 *  `|B| => B -> OtherMixin -> ExtendMixin -> Mixin -> A`
 */
class ClassRegistry {
    constructor() {
        // base name map
        this.baseNameMap = {};
        // Object that maps `baseClass` to the class implementation extended in-place.
        this.includedMap = new Map();
        // Object that maps `baseClassCB` to the array of callbacks to generate the extended class.
        this.extendedCBMap = new Map();
        // Object that maps `baseClassCB` extended class to the `baseClass` of its super in the includedMap.
        this.extendedSuperMap = new Map();
        // For faster access, we can `freeze` the registry so that instead of dynamically generating
        // the extended classes, it is taken from the cache instead.
        this.cache = new Map();
    }
    /**
     * Add a new class in the Registry.
     * @param {Function} baseClass `class`
     */
    add(baseClass) {
        this.includedMap.set(baseClass, []);
        this.baseNameMap[baseClass.name] = baseClass;
    }
    /**
     * Add a new class in the Registry based on other class
     * in the registry.
     * @param {Function} baseClassCB `class -> class`
     * @param {Function} base `class | class -> class`
     */
    addByExtending(baseClassCB, base) {
        this.extendedCBMap.set(baseClassCB, [baseClassCB]);
        this.extendedSuperMap.set(baseClassCB, base);
        this.baseNameMap[baseClassCB.name] = baseClassCB;
    }
    /**
     * Extend in-place a class in the registry. E.g.
     * ```
     * // Using the following notation:
     * //  * |A| -  compiled class in the registry
     * //  *  A  -  class or an extension callback
     * //  * |A| => A2 -> A1 -> A
     * //       -  the above means, compiled class A
     * //          points to the class inheritance derived from
     * //          A2(A1(A))
     *
     * class A {};
     * Registry.add(A);
     * // |A| => A
     *
     * let A1 = x => class extends x {};
     * Registry.extend(A, A1);
     * // |A| => A1 -> A
     *
     * let B = x => class extends x {};
     * Registry.addByExtending(B, A);
     * // |B| => B -> |A|
     * // |B| => B -> A1 -> A
     *
     * let B1 = x => class extends x {};
     * Registry.extend(B, B1);
     * // |B| => B1 -> B -> |A|
     *
     * let C = x => class extends x {};
     * Registry.addByExtending(C, B);
     * // |C| => C -> |B|
     *
     * let B2 = x => class extends x {};
     * Registry.extend(B, B2);
     * // |B| => B2 -> B1 -> B -> |A|
     *
     * // Overall:
     * // |A| => A1 -> A
     * // |B| => B2 -> B1 -> B -> A1 -> A
     * // |C| => C -> B2 -> B1 -> B -> A1 -> A
     * ```
     * @param {Function} base `class | class -> class`
     * @param {Function} extensionCB `class -> class`
     */
    extend(base, extensionCB) {
        if (typeof base === "string") {
            base = this.baseNameMap[base];
        }
        let extensionArray;
        if (this.includedMap.get(base)) {
            extensionArray = this.includedMap.get(base);
        } else if (this.extendedCBMap.get(base)) {
            extensionArray = this.extendedCBMap.get(base);
        } else {
            throw new Error(
                `'${base.name}' is not in the Registry. Add it to Registry before extending.`
            );
        }
        extensionArray.push(extensionCB);
        const locOfNewExtension = extensionArray.length - 1;
        const self = this;
        const oldCompiled = this.isFrozen ? this.cache.get(base) : null;
        return {
            remove() {
                extensionArray.splice(locOfNewExtension, 1);
                self._recompute(base, oldCompiled);
            },
            compile() {
                self._recompute(base);
            },
        };
    }
    _compile(base) {
        let res;
        if (this.includedMap.has(base)) {
            res = this.includedMap.get(base).reduce((acc, ext) => ext(acc), base);
        } else {
            const superClass = this.extendedSuperMap.get(base);
            const extensionCBs = this.extendedCBMap.get(base);
            res = extensionCBs.reduce((acc, ext) => ext(acc), this._compile(superClass));
        }
        Object.defineProperty(res, "name", { value: base.name });
        return res;
    }
    /**
     * Return the compiled class (containing all the extensions) of the base class.
     * @param {Function} base `class | class -> class` function used in adding the class
     */
    get(base) {
        if (typeof base === "string") {
            base = this.baseNameMap[base];
        }
        if (this.isFrozen) {
            return this.cache.get(base);
        }
        return this._compile(base);
    }
    /**
     * Uses the callbacks registered in the registry to compile the classes.
     */
    freeze() {
        // Step: Compile the `included classes`.
        for (const [baseClass, extensionCBs] of this.includedMap.entries()) {
            const compiled = extensionCBs.reduce((acc, ext) => ext(acc), baseClass);
            this.cache.set(baseClass, compiled);
        }

        // Step: Compile the `extended classes` based on `included classes`.
        // Also gather those the are based on `extended classes`.
        const remaining = [];
        for (const [baseClassCB, extensionCBArray] of this.extendedCBMap.entries()) {
            const compiled = this.cache.get(this.extendedSuperMap.get(baseClassCB));
            if (!compiled) {
                remaining.push([baseClassCB, extensionCBArray]);
                continue;
            }
            const extendedClass = extensionCBArray.reduce(
                (acc, extensionCB) => extensionCB(acc),
                compiled
            );
            this.cache.set(baseClassCB, extendedClass);
        }

        // Step: Compile the `extended classes` based on `extended classes`.
        for (const [baseClassCB, extensionCBArray] of remaining) {
            const compiled = this.cache.get(this.extendedSuperMap.get(baseClassCB));
            const extendedClass = extensionCBArray.reduce(
                (acc, extensionCB) => extensionCB(acc),
                compiled
            );
            this.cache.set(baseClassCB, extendedClass);
        }

        // Step: Set the name of the compiled classess
        for (const [base, compiledClass] of this.cache.entries()) {
            Object.defineProperty(compiledClass, "name", { value: base.name });
        }

        // Step: Set the flag to true;
        this.isFrozen = true;
    }
    _recompute(base, old) {
        if (typeof base === "string") {
            base = this.baseNameMap[base];
        }
        return old ? old : this._compile(base);
    }
}

export default ClassRegistry;
