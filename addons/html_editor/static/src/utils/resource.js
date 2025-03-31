export const resourceSequenceSymbol = Symbol("resourceSequence");

export function withSequence(sequenceNumber, object) {
    return {
        [resourceSequenceSymbol]: sequenceNumber,
        object,
    };
}
