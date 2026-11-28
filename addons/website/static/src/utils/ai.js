/**
 * Splits items into chunks whose size stays under the limit. An item bigger
 * than the limit gets a chunk of its own.
 *
 * @param {Array} items
 * @param {Function} getSize - gives the size of an item
 * @param {number} limit - max size of a chunk
 * @returns {Array[]}
 */
export function chunkBySize(items, getSize, limit) {
    const chunks = [];
    let chunkSize = 0;
    for (const item of items) {
        const size = getSize(item);
        if (!chunks.length || chunkSize + size > limit) {
            chunks.push([]);
            chunkSize = 0;
        }
        chunks.at(-1).push(item);
        chunkSize += size;
    }
    return chunks;
}

/**
 * Calls `fn` on each item, with at most `limit` calls running at a time.
 *
 * @param {Array} items
 * @param {Function} fn - async function called with an item
 * @param {number} limit - max calls at a time
 * @returns {Promise<Array>} the results, in the order of the items
 */
export async function mapWithConcurrency(items, fn, limit) {
    const results = [];
    let nextIndex = 0;
    const callNext = async () => {
        while (nextIndex < items.length) {
            const index = nextIndex++;
            results[index] = await fn(items[index]);
        }
    };
    await Promise.all(Array.from({ length: limit }, callNext));
    return results;
}
