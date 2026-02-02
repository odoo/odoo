export const resourceSequenceSymbol = Symbol("resourceSequence");

/**
 * @template T
 * @typedef {Object} ResourceWithSequence
 * @property {T} object
 */

/**
 * @template T
 * @param {number} sequenceNumber
 * @param {...T} objects - One or more objects to assign the sequence number to
 * Single wrapped object if one object passed, array if multiple
 * @returns {ResourceWithSequence<T> | ResourceWithSequence<T>[]}
 */
export function withSequence(sequenceNumber, ...objects) {
    if (typeof sequenceNumber !== "number") {
        throw new Error(
            `sequenceNumber must be a number. Got ${sequenceNumber} (${typeof sequenceNumber}).`
        );
    }
    if (objects.length === 0) {
        throw new Error("At least one object must be provided to withSequence.");
    }

    const wrappedObjects = objects.map((object) => ({
        [resourceSequenceSymbol]: sequenceNumber,
        object,
    }));

    // Return single object for backward compatibility with non-array resources
    // Return array when multiple objects are passed (for spreading in arrays)
    return wrappedObjects.length === 1 ? wrappedObjects[0] : wrappedObjects;
}
