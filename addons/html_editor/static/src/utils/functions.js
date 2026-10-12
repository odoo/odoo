/**
 * Creates a version of the function that's memoized on the value of its first
 * argument, which must be an Object.
 * This is a version of @web's memoize, with the difference that it uses a
 * WeakMap instead of a Map, making it more suitable for functions that take
 * objects as arguments, as it avoids memory leaks by allowing the garbage
 * collector to clean up unused objects.
 *
 * @template T, U
 * @param {(arg: T) => U} func the function to memoize
 * @returns {(arg: T) => U} a memoized version of the original function
 */
export function weakMemoize(func) {
    const cache = new WeakMap();
    const funcName = func.name ? func.name + " (memoized)" : "memoized";
    return {
        [funcName](firstArg, ...args) {
            if (!cache.has(firstArg)) {
                cache.set(firstArg, func(firstArg, ...args));
            }
            return cache.get(firstArg);
        },
    }[funcName];
}
