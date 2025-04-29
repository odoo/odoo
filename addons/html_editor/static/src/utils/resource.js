export const resourceSequenceSymbol = Symbol("resourceSequence");

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
