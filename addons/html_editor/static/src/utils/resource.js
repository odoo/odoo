export const resourceSequenceSymbol = Symbol("resourceSequence");

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
