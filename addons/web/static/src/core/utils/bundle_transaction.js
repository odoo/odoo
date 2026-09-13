// @ts-check
/** @odoo-module native */

let depth = 0;

/** @type {Set<() => any>} */
const pending = new Set();

/** @type {{ promise: Promise<void>, resolve: () => void } | null} */
let drain = null;

async function settle() {
    const callbacks = [...pending];
    pending.clear();
    const waiting = drain;
    drain = null;
    for (const callback of callbacks) {
        try {
            await callback();
        } catch (error) {
            console.error("[bundle] deferred callback failed:", error);
        }
    }
    waiting?.resolve();
}

/**
 * @template T
 * @param {() => Promise<T>} evaluate
 * @returns {Promise<T>}
 */
export async function runInBundleTransaction(evaluate) {
    depth++;
    try {
        return await evaluate();
    } finally {
        depth--;
        if (depth === 0) {
            if (pending.size) {
                await settle();
            }
        } else if (pending.size) {
            // another bundle is still evaluating, so the reactions this one
            // raised run at that bundle's end; this one resolves applied, not
            // merely evaluated, or a component mounted on it asks for a
            // service that is registered and not started. Two bundles that
            // load concurrently is the case; a module awaiting a bundle at
            // its top level (none does) would wait for itself here.
            drain ??= Promise.withResolvers();
            await drain.promise;
        }
    }
}

/**
 * @param {() => any} callback
 * @returns {boolean}
 */
export function deferUntilBundlesSettled(callback) {
    if (depth === 0) {
        return false;
    }
    pending.add(callback);
    return true;
}

/** @returns {boolean} */
export function isBundleEvaluating() {
    return depth > 0;
}

export function resetBundleTransactions() {
    depth = 0;
    pending.clear();
    drain?.resolve();
    drain = null;
}
