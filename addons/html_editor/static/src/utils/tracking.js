/**
 * Creates a function to track whether a key has been seen before.
 * The returned function returns true for the first occurrence of each key,
 * false for subsequent ones.
 */
export function trackOccurrences() {
    const visited = new Set();
    return function isFirstOccurrence(key) {
        if (visited.has(key)) {
            return false;
        }
        visited.add(key);
        return true;
    };
}

/**
 * Creates a function to track whether a pair of keys has been seen before.
 * The returned function returns true for the first occurrence of each pair of
 * keys, false for subsequent ones.
 * Order matters, i.e. (a, b) is not the same as (b, a).
 */
export function trackOccurrencesPair() {
    const visited = new Map();
    /** @type {(a, b) => boolean} */
    return function isFirstOccurrence(a, b) {
        if (!visited.has(a)) {
            visited.set(a, trackOccurrences());
        }
        return visited.get(a)(b);
    };
}
