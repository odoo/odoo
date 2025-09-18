// @ts-check

/** @module @web/model/relational_model/resequence - Reorders records by sequence field via drag-and-drop position changes */

/**
 * Resequence records based on provided parameters.
 *
 * @param {Object} params
 * @param {Array} params.records - The list of records to resequence.
 * @param {string} params.resModel - The model to be used for resequencing.
 * @param {Object} params.orm
 * @param {string} params.fieldName - The field used to handle the sequence.
 * @param {number} params.movedId - The id of the record being moved.
 * @param {number} [params.targetId] - The id of the target position, the record will be resequenced
 *                                     after the target. If undefined, the record will be resequenced
 *                                     as the first record.
 * @param {Boolean} [params.asc] - Resequence in ascending or descending order
 * @param {(record: any) => number} [params.getSequence] - Function to get the sequence of a record.
 * @param {(record: any) => number} [params.getResId] - Function to get the resID of the record.
 * @param {Object} [params.context]
 * @returns {Promise<any>} - The list of the resequenced fieldName
 */
export async function resequence({
    records,
    resModel,
    orm,
    fieldName,
    movedId,
    targetId,
    asc = true,
    getSequence = (record) => record[fieldName],
    getResId = (record) => record.id,
    context,
}) {
    // Find indices
    const fromIndex = records.findIndex((d) => d.id === movedId);
    let toIndex = 0;
    if (targetId !== null) {
        const targetIndex = records.findIndex((d) => d.id === targetId);
        toIndex = fromIndex > targetIndex ? targetIndex + 1 : targetIndex;
    }

    // Determine which records/groups need to be modified
    const firstIndex = Math.min(fromIndex, toIndex);
    const lastIndex = Math.max(fromIndex, toIndex) + 1;
    let reorderAll = records.some((record) => getSequence(record) === undefined);
    if (!reorderAll) {
        let lastSequence = (asc ? -1 : 1) * Infinity;
        for (let index = 0; index < records.length; index++) {
            const sequence = getSequence(records[index]);
            if (
                (asc && lastSequence >= sequence) ||
                (!asc && lastSequence <= sequence)
            ) {
                reorderAll = true;
                break;
            }
            lastSequence = sequence;
        }
    }

    // Save the original list in case of error
    const originalOrder = [...records];
    // Perform the resequence in the list of records/groups
    const record = records[fromIndex];
    if (fromIndex !== toIndex) {
        records.splice(fromIndex, 1);
        records.splice(toIndex, 0, record);
    }

    // Creates the list of records/groups to modify
    let toReorder = records;
    if (!reorderAll) {
        toReorder = toReorder
            .slice(firstIndex, lastIndex)
            .filter((r) => r.id !== movedId);
        if (fromIndex < toIndex) {
            toReorder.push(record);
        } else {
            toReorder.unshift(record);
        }
    }
    if (!asc) {
        toReorder.reverse();
    }

    const resIds = toReorder.map((d) => getResId(d)).filter((id) => id && !isNaN(id));
    const sequences = toReorder.map(getSequence);
    const offset = Math.min(...sequences) || 0;

    // Try to write new sequences on the affected records/groups
    try {
        return await orm.webResequence(resModel, resIds, {
            field_name: fieldName,
            offset,
            context,
            specification: { [fieldName]: {} },
        });
    } catch (error) {
        // If the server fails to resequence, rollback the original list
        records.splice(0, records.length, ...originalOrder);
        throw error;
    }
}
