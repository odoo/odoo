/** @odoo-module **/

/**
 * Creates a version of the function that's memoized on the value of its first
 * argument.
 *
 * @template T, U
 * @param {(arg: T) => U} func the function to memoize
 * @returns {(arg: T) => U} a memoized version of the original function
 */
export function memoize(func) {
    const cache = new Map();
    return function (...args) {
        if (!cache.has(args[0])) {
            cache.set(args[0], func(...args));
        }
        return cache.get(...args);
    };
}
