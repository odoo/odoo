/* Returns an array containing all elements of the given
 * array corresponding to the rule function {agg} and without duplicates
 *
 * @template T
 * @template F
 * @param {T[]} array
 * @param {F} function
 * @returns {T[]}
 */
export function uniqueBy(array, agg) {
    const map = new Map();
    for (const item of array) {
        const key = agg(item);
        if (!map.has(key)) {
            map.set(key, item);
        }
    }
    return [...map.values()];
}
