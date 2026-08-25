import { computed, getScope, signal } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";

/**
 * A computed that arms the timeout marking its own value stale, so a value
 * nobody reads schedules nothing and its scope drops the last timeout.
 *
 * @template T
 * @param {() => T} compute
 * @param {(value: T) => number|void} msUntilStale delay before the value has
 *  to be made again, or nothing to leave it as it is
 * @returns {() => T}
 */
export function computedUntilStale(compute, msUntilStale) {
    const staleness = signal(0);
    const markStale = incrementFn(staleness);
    let timeout;
    getScope()?.onDestroy(() => browser.clearTimeout(timeout));
    return computed(() => {
        void staleness();
        browser.clearTimeout(timeout);
        const value = compute();
        const ms = msUntilStale(value);
        if (ms) {
            timeout = browser.setTimeout(markStale, Math.ceil(ms));
        }
        return value;
    });
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
