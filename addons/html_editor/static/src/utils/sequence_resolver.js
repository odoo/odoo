import { sequenceNumber } from "./resource";

/**
 * Resolves the final numerical sequence for a list of sequenced objects.
 * This function handles 'before' and 'after' dependencies.
 *
 * @param {Array} sequencedObjects An array of objects returned by withSequence.
 * @returns {Array} The same objects, but with their resourceSequenceSymbol resolved to a number.
 */
export function resolveSequences(sequencedObjects) {
    const resolved = new Map(); // Map of constantName -> resolvedSequenceNumber
    const pending = []; // List of { obj, definition } for objects with 'before'/'after'

    // First pass: resolve numerical sequences and collect pending dependencies
    for (const item of sequencedObjects) {
        const definition = item[sequenceNumber];
        if (typeof definition === "number") {
            resolved.set(item.object, definition); // Assuming the object itself can be a reference
        } else if (typeof definition === "object" && definition !== null) {
            pending.push({ obj: item.object, definition });
        } else {
            // Handle cases where sequenceDefinition is not a number or a known object type
            // For now, treat as a default or throw an error.
            // For simplicity, let's assign a default if it's not a number or a before/after object.
            resolved.set(item.object, 0); // Default to 0 if unknown type
        }
    }

    let changed = true;
    let iteration = 0;
    const MAX_ITERATIONS = 100; // Prevent infinite loops for circular dependencies

    while (changed && pending.length > 0 && iteration < MAX_ITERATIONS) {
        changed = false;
        iteration++;
        for (let i = pending.length - 1; i >= 0; i--) {
            const { obj, definition } = pending[i];
            const refValue = resolved.get(definition.ref); // Get the resolved value of the reference constant

            if (typeof refValue === "number") {
                let newSequence;
                if (definition.type === "before") {
                    // Find the previous resolved sequence before refValue
                    let prevResolved = -Infinity;
                    for (const val of resolved.values()) {
                        if (val < refValue && val > prevResolved) {
                            prevResolved = val;
                        }
                    }
                    newSequence = (refValue + prevResolved) / 2;
                } else if (definition.type === "after") {
                    // Find the next resolved sequence after refValue
                    let nextResolved = Infinity;
                    for (const val of resolved.values()) {
                        if (val > refValue && val < nextResolved) {
                            nextResolved = val;
                        }
                    }
                    newSequence = (refValue + nextResolved) / 2;
                }
                resolved.set(obj, newSequence);
                pending.splice(i, 1); // Remove from pending
                changed = true;
            }
        }
    }

    if (pending.length > 0) {
        console.warn(
            "Could not resolve all sequences due to unresolved dependencies or circular references:",
            pending
        );
        // Assign default values to remaining pending items to avoid errors
        for (const { obj } of pending) {
            resolved.set(obj, 0); // Assign a default if unresolved
        }
    }

    // Reconstruct the original array with resolved sequence numbers
    return sequencedObjects
        .map((item) => {
            const resolvedSequence = resolved.get(item.object);
            if (typeof resolvedSequence === "number") {
                item[sequenceNumber] = resolvedSequence;
            } else {
                // Fallback if for some reason it wasn't resolved (should be caught by pending.length > 0 check)
                item[sequenceNumber] = 0;
            }
            return item;
        })
        .sort((a, b) => a[sequenceNumber] - b[sequenceNumber]);
}
