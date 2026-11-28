/** @odoo-module */

import { getRunner } from "../main_runner";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { Map } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * Returns a subclass of the given native class, keeping track of the instances
 * acquiring resources during a test, to release them after it.
 *
 * @template {new (...args: any[]) => any} T
 * @param {T} NativeClass
 * @param {string | null} acquire
 * @param {string} release
 * @returns {T}
 */
function makeDisposableClass(NativeClass, acquire, release) {
    const { name } = NativeClass;
    const originalRelease = NativeClass.prototype[release];
    if (acquire) {
        const originalAcquire = NativeClass.prototype[acquire];
        // `acquire` defined: override the method on the disposable class
        return {
            [name]: class extends NativeClass {
                [acquire]() {
                    trackInstance(this, release);
                    return originalAcquire.apply(this, arguments);
                }
                [release]() {
                    disposableInstances.delete(this);
                    return originalRelease.apply(this, arguments);
                }
            },
        }[name];
    } else {
        // No `acquire`: track instances from the constructor
        return {
            [name]: class extends NativeClass {
                constructor() {
                    super(...arguments);
                    trackInstance(this, release);
                }
                [release]() {
                    disposableInstances.delete(this);
                    return originalRelease.apply(this, arguments);
                }
            },
        }[name];
    }
}

/**
 * Instances created outside of tests (e.g. by Hoot's own UI) are not tracked,
 * as their lifecycle is not bound to any test.
 *
 * @param {object} instance
 * @param {string} release
 */
function trackInstance(instance, release) {
    if (getRunner()?.getCurrent().suite) {
        disposableInstances.set(instance, release);
    }
}

/**
 * Native classes holding resources (e.g. observed nodes, open connections) until
 * explicitly released, which would otherwise outlive the test that acquired them.
 *
 * Each class is mapped to the method acquiring its resources (`null` if they are
 * acquired on instantiation), and to the method releasing them, which must be
 * harmless to call more than once.
 *
 * @type {[name: string, acquire: string | null, release: string][]}
 */
const DISPOSABLE_CLASSES = [
    ["IntersectionObserver", "observe", "disconnect"],
    ["MutationObserver", "observe", "disconnect"],
    ["PerformanceObserver", "observe", "disconnect"],
    ["ReportingObserver", "observe", "disconnect"],
    ["ResizeObserver", "observe", "disconnect"],
];

/** @type {Map<object, string>} */
const disposableInstances = new Map();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupResources() {
    for (const [instance, release] of disposableInstances) {
        let result;
        try {
            result = instance[release]();
        } catch {
            // Ignore errors during release
        }
        // Asynchronous release methods may reject when already released
        if (typeof result?.catch === "function") {
            result.catch(() => {});
        }
    }
    disposableInstances.clear();
}

/**
 * Returns the window descriptors of the disposable versions of the native classes
 * listed in {@link DISPOSABLE_CLASSES}, if available in the given window.
 *
 * @param {typeof globalThis} view
 */
export function getDisposableDescriptors(view) {
    /** @type {Record<string, PropertyDescriptor>} */
    const descriptors = {};
    for (const [name, acquire, release] of DISPOSABLE_CLASSES) {
        // Some of the classes are not available in all browsers
        if (typeof view[name] === "function") {
            descriptors[name] = { value: makeDisposableClass(view[name], acquire, release) };
        }
    }
    return descriptors;
}
