import { computed, getScope, shallowEqual, signal } from "@odoo/owl";

/**
 * A computed that arms the timeout marking its own value stale, so a value
 * nobody reads schedules nothing and its scope drops the last timeout.
 *
 * @template T
 * @param {() => T} compute
 * @param {(value: T) => number|void} msUntilStale delay before the value has
 *  to be made again, or nothing to leave it as it is
 * @param {import("@odoo/owl").ComputedOptions<T>} [options]
 * @returns {() => T}
 */
export function computedUntilStale(compute, msUntilStale, options) {
    const staleness = signal(0);
    const markStale = incrementFn(staleness);
    let timeout;
    getScope()?.onDestroy(() => window.clearTimeout(timeout));
    return computed(() => {
        void staleness();
        window.clearTimeout(timeout);
        const value = compute();
        const ms = msUntilStale(value);
        if (ms) {
            timeout = window.setTimeout(markStale, Math.ceil(ms));
        }
        return value;
    }, options);
}

/**
 * Like owl's `shallowEqual`, but recurses into plain arrays/objects: for a computed
 * returning a fresh array of freshly built arrays/objects (e.g. grouped/partitioned
 * actions), `shallowEqual` never matches.
 *
 * @param {any[]|Record<string, any>} a
 * @param {any[]|Record<string, any>} b
 * @returns {boolean}
 */
export function nestedShallowEqual(a, b) {
    if (shallowEqual(a, b)) {
        return true;
    }
    if (Array.isArray(a) && Array.isArray(b)) {
        return a.length === b.length && a.every((x, i) => nestedShallowEqual(x, b[i]));
    }
    if (typeof a !== "object" || typeof b !== "object" || a === null || b === null) {
        return false;
    }
    const protoA = Object.getPrototypeOf(a);
    const protoB = Object.getPrototypeOf(b);
    if (
        (protoA !== Object.prototype && protoA !== null) ||
        (protoB !== Object.prototype && protoB !== null)
    ) {
        return false;
    }
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    return (
        keysA.length === keysB.length &&
        keysA.every(
            (key) =>
                Object.prototype.hasOwnProperty.call(b, key) && nestedShallowEqual(a[key], b[key])
        )
    );
}

/**
 * Returns a function to increment the value of a number signal. The initial
 * state is taken when the resulting function is ran, not when incrementFn is
 * called. This ensures the increment is always applied even if the initial
 * render is outdated.
 *
 * @param {import("@odoo/owl").Signal<number>} signal
 * @returns {() => void} A function to increment the signal value.
 */
export function incrementFn(signal, value = 1) {
    return () => signal.set(signal() + value);
}

/**
 * Returns a function to toggle the value of a boolean signal. The initial state
 * is taken when toggleFn is called, not when the resulting function is ran.
 * This synchronizes the result of the function with the currently displayed
 * state to avoid unexpected behaviors.
 *
 * @param {import("@odoo/owl").Signal<boolean>} signal
 * @returns {() => void} A function to toggle the signal value.
 */
export function toggleFn(signal) {
    return signal() ? () => signal.set(false) : () => signal.set(true);
}
