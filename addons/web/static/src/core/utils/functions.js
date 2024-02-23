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

/**
 * Generate a unique integer id (unique within the entire client session).
 * Useful for temporary DOM ids.
 *
 * @param {string} prefix
 * @returns {string}
 */
export function uniqueId(prefix = "") {
    return `${prefix}${++uniqueId.nextId}`;
}
// set nextId on the function itself to be able to patch then
uniqueId.nextId = 0;

export function iter(iterable) {
    const gen = (function* (iterable) {
        yield* iterable;
    })(iterable);
    const next = gen.next;
    gen.next = function (_value) {
        const _next = next.call(this, _value);
        this.current = _next.value;
        return _next;
    };
    return gen;
}
export function next(iterator) {
    const { value, done } = iterator.next();
    if (!done) {
        return value;
    }
    return undefined;
}
