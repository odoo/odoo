export const resourceSequenceSymbol = Symbol("resourceSequence");

/**
 * Sequence marker used with `withSequence` to ensure the wrapped handler
 * runs before other handlers of the same resource.
 *
 * Intended for DOM read logic so it executes before potential DOM mutations,
 * avoiding layout thrashing.
 */
export const READ = 0;

/**
 * @template T
 * @typedef {Object} ResourceWithSequence
 * @property {T} object
 */

/**
 * @template T
 * @param {number} sequenceNumber
 * @param {T} object
 * @returns {ResourceWithSequence<T>}
 */
export function withSequence(sequenceNumber, object) {
    if (typeof sequenceNumber !== "number") {
        throw new Error(
            `sequenceNumber must be a number. Got ${sequenceNumber} (${typeof sequenceNumber}).`
        );
    }
    return {
        [resourceSequenceSymbol]: sequenceNumber,
        object,
    };
}
