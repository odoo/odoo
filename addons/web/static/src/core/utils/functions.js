/** @odoo-module **/

/**
 * Creates a version of the function that's memoized on the value of its first
 * argument, if any.
 *
 * @template T, U
 * @param {(arg: T) => U} func the function to memoize
 * @returns {(arg: T) => U} a memoized version of the original function
 */
export function memoize(func) {
    const cache = new Map();
    const funcName = func.name ? func.name + " (memoized)" : "memoized";
    return {
        [funcName](...args) {
            if (!cache.has(args[0])) {
                cache.set(args[0], func(...args));
            }
            return cache.get(...args);
        },
    }[funcName];
}
