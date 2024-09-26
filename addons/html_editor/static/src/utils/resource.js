export const resourceSequenceSymbol = Symbol("resourceSequence");

export function withSequence(sequenceNumber, object) {
    return {
        [resourceSequenceSymbol]: sequenceNumber,
        object,
    };
}

/**
 * Execute a series of handlers until one of them returns a truthy value.
 *
 * This function is meant to enhances code readability by clearly expressing its
 * intent.
 *
 * A command "delegate" its execution to one of the handlers. It is the
 * responsibility of the caller to stop the execution when a handler returns a
 * truthy value.
 *
 * Example:
 * ```js
 * if (delegate(myHandlers, arg1, arg2)) {
 *   return;
 * }
 * ```
 *
 * @param {Function[]} handlers A list of handlers to execute. The function
 * should return a truthy value to signal it has been handled.
 * @param  {...any} args
 */
export function delegate(handlers, ...args) {
    return handlers.some((fn) => fn(...args));
}
