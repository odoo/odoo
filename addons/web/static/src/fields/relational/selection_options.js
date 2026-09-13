// @ts-check
/** @odoo-module native */

/**
 * Retain selected records without removing the ordinary option query's limit.
 * Missing records are fetched with the caller's context and access rules, not
 * synthesized from labels that may have been read in a different context.
 *
 * @template T
 * @param {T[]} options
 * @param {number[]} selectedIds
 * @param {(option: T) => number} getId
 * @param {(ids: number[]) => Promise<T[]>} loadMissing
 * @returns {Promise<T[]>}
 */
export async function completeSelectedOptions(
    options,
    selectedIds,
    getId,
    loadMissing,
) {
    const shownIds = new Set(options.map(getId));
    const missingIds = selectedIds.filter((id) => !shownIds.has(id));
    if (!missingIds.length) {
        return options;
    }
    return [...options, ...(await loadMissing(missingIds))];
}
