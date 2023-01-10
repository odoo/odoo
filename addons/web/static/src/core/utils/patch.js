/** @odoo-module **/

const patchMap = new WeakMap();

/**
 * Patch an object
 *
 * If the intent is to patch a class, don't forget to patch the prototype, unless
 * you want to patch static properties/methods.
 *
 * @param {Object} obj Object to patch
 * @param {string} patchName
 * @param {Object} patchValue
 * @param {{pure?: boolean}} [options]
 */
export function patch(obj, patchName, patchValue, options = {}) {
    const pure = Boolean(options.pure);
    if (!patchMap.has(obj)) {
        patchMap.set(obj, {
            original: {},
            patches: [],
        });
    }
    const objDesc = patchMap.get(obj);
    if (objDesc.patches.some((p) => p.name === patchName)) {
        throw new Error(`Class ${obj.name} already has a patch ${patchName}`);
    }
    objDesc.patches.push({
        name: patchName,
        patch: patchValue,
        pure,
    });

    for (const k in patchValue) {
        let prevDesc = null;
        let proto = obj;
        do {
            prevDesc = Object.getOwnPropertyDescriptor(proto, k);
            proto = Object.getPrototypeOf(proto);
        } while (!prevDesc && proto);

        let newDesc = Object.getOwnPropertyDescriptor(patchValue, k);
        if (!objDesc.original.hasOwnProperty(k)) {
            objDesc.original[k] = Object.getOwnPropertyDescriptor(obj, k);
        }

        if (prevDesc) {
            const patchedFnName = `${k} (patch ${patchName})`;

            if (prevDesc.value && typeof newDesc.value === "function") {
                newDesc = { ...prevDesc, value: newDesc.value };
                makeIntermediateFunction("value", prevDesc, newDesc, patchedFnName);
            }
            if ((newDesc.get || newDesc.set) && (prevDesc.get || prevDesc.set)) {
                // get and set are defined together. If they are both defined
                // in the previous descriptor but only one in the new descriptor
                // then the other will be undefined so we need to apply the
                // previous descriptor in the new one.
                newDesc = {
                    ...prevDesc,
                    get: newDesc.get || prevDesc.get,
                    set: newDesc.set || prevDesc.set,
                };
                if (prevDesc.get && typeof newDesc.get === "function") {
                    makeIntermediateFunction("get", prevDesc, newDesc, patchedFnName);
                }
                if (prevDesc.set && typeof newDesc.set === "function") {
                    makeIntermediateFunction("set", prevDesc, newDesc, patchedFnName);
                }
            }
        }

        Object.defineProperty(obj, k, newDesc);
    }

    function makeIntermediateFunction(key, prevDesc, newDesc, patchedFnName) {
        const _superFn = prevDesc[key];
        const patchFn = newDesc[key];
        if (pure) {
            newDesc[key] = patchFn;
        } else {
            newDesc[key] = {
                [patchedFnName](...args) {
                    let prevSuper;
                    if (this) {
                        prevSuper = this._super;
                        Object.defineProperty(this, "_super", {
                            value: _superFn.bind(this),
                            configurable: true,
                            writable: true,
                        });
                    }
                    const result = patchFn.call(this, ...args);
                    if (this) {
                        Object.defineProperty(this, "_super", {
                            value: prevSuper,
                            configurable: true,
                            writable: true,
                        });
                    }
                    return result;
                },
            }[patchedFnName];
        }
    }
}

/**
 * We define here an unpatch function.  This is mostly useful if we want to
 * remove a patch.  For example, for testing purposes
 *
 * @param {Object} obj
 * @param {string} patchName
 */
export function unpatch(obj, patchName) {
    const objDesc = patchMap.get(obj);
    if (!objDesc.patches.some((p) => p.name === patchName)) {
        throw new Error(`Class ${obj.name} does not have any patch ${patchName}`);
    }
    patchMap.delete(obj);

    // Restore original methods on the prototype and the class.
    for (const k in objDesc.original) {
        if (objDesc.original[k] === undefined) {
            delete obj[k];
        } else {
            Object.defineProperty(obj, k, objDesc.original[k]);
        }
    }

    // Re-apply the patches except the one to remove.
    for (const patchDesc of objDesc.patches) {
        if (patchDesc.name !== patchName) {
            patch(obj, patchDesc.name, patchDesc.patch, { pure: patchDesc.pure });
        }
    }
}
