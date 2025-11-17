export const attributeFlatter = (attribute) =>
    Object.values(attribute)
        .map((v) => {
            if (v instanceof Object) {
                return Object.entries(v)
                    .filter((v) => v[1])
                    .map((v) => v[0]);
            } else {
                return v;
            }
        })
        .flat()
        .map((v) => parseInt(v));

/**
 * Returns a new array containing elements from the input array
 * until the predicate returns false. Iteration stops at the first failure.
 *
 * @template T
 * @param {T[]} items - The array to iterate over.
 * @param {(item: T, index: number, array: T[]) => boolean} predicate - Function invoked per iteration.
 * @returns {T[]} - A new array with elements taken from the start until the predicate fails.
 */
export const filterWhile = (items, predicate) => {
    const result = [];
    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (!predicate(item, i, items)) {
            break;
        }
        result.push(item);
    }
    return result;
};

/**
 * Creates a shallow clone of an object while preserving its prototype,
 * and optionally adding extra properties.
 *
 * This is especially useful when working with proxy-like objects,
 * where standard object spreading (e.g. `{ ...obj }`) can cause the loss of some properties.
 *
 * @param {Object} obj - The object to clone.
 * @param {Object} [extra={}] - Optional extra properties to merge into the clone.
 * @returns {Object} A new object that preserves the original prototype and merges any additional properties.
 */
export const cloneProxy = (obj, extra = {}) =>
    Object.assign(Object.create(Object.getPrototypeOf(obj)), obj, extra);
