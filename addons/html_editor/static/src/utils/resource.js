export const resourceSequenceSymbol = Symbol("resourceSequence");

/**
 * Sequence marker used with `withSequence` to ensure the wrapped handler
 * runs before other handlers of the same resource.
 *
 * Intended for DOM read logic so it executes before potential DOM mutations,
 * avoiding layout thrashing.
 */
export const READ = 0;

export function withSequence(sequenceNumber, object) {
    return {
        [resourceSequenceSymbol]: sequenceNumber,
        object,
    };
}
