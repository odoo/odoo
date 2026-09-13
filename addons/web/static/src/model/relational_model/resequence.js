// @ts-check
/** @odoo-module native */

/**
 * @param {Object} params
 * @param {Array<{id: number | string}>} params.records
 * @param {number | string} params.movedId
 * @param {number | string | null} [params.targetId]
 * @param {(record: any) => number} params.getSequence
 * @param {boolean} [params.asc]
 * @returns {{
 * toReorder: any[],
 * offset: number,
 * fromIndex: number,
 * toIndex: number,
 * reorderAll: boolean,
 * }}
 */
export function computeResequencePlan({
    records,
    movedId,
    targetId,
    getSequence,
    asc = true,
}) {
    const fromIndex = records.findIndex((r) => r.id === movedId);
    const targetIndex =
        targetId == null ? -1 : records.findIndex((r) => r.id === targetId);
    if (fromIndex < 0 || (targetId != null && targetIndex < 0)) {
        return {
            toReorder: [],
            offset: 0,
            fromIndex,
            toIndex: fromIndex,
            reorderAll: false,
        };
    }
    let toIndex = 0;
    if (targetId !== null && targetId !== undefined) {
        toIndex = fromIndex > targetIndex ? targetIndex + 1 : targetIndex;
    }

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

    const reordered = [...records];
    const [record] = reordered.splice(fromIndex, 1);
    reordered.splice(toIndex, 0, record);

    const toReorder = reorderAll ? reordered : reordered.slice(firstIndex, lastIndex);
    if (!asc) {
        toReorder.reverse();
    }

    const sequences = toReorder.map(getSequence).filter((s) => s != null && !isNaN(s));
    const offset = sequences.length ? Math.min(...sequences) : 0;

    return { toReorder, offset, fromIndex, toIndex, reorderAll };
}

/**
 * @param {Object} params
 * @param {any[]} params.records
 * @param {string} params.resModel
 * @param {Record<string, any>} params.orm
 * @param {string} params.fieldName
 * @param {number | string} params.movedId
 * @param {number | string | null} [params.targetId]
 * @param {Boolean} [params.asc]
 * @param {(record: any) => number} [params.getSequence]
 * @param {(record: any) => number} [params.getResId]
 * @param {Object} [params.context]
 * @returns {Promise<any>}
 */
export async function resequenceRecords({
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
    const { toReorder, offset, fromIndex, toIndex } = computeResequencePlan({
        records,
        movedId,
        targetId,
        getSequence,
        asc,
    });

    if (!toReorder.length) {
        return [];
    }

    const originalOrder = [...records];
    const record = records[fromIndex];
    if (fromIndex !== toIndex) {
        records.splice(fromIndex, 1);
        records.splice(toIndex, 0, record);
    }

    const resIds = toReorder.map((d) => getResId(d)).filter((id) => id && !isNaN(id));

    try {
        return await orm.webResequence(resModel, resIds, {
            field_name: fieldName,
            offset,
            context,
            specification: { [fieldName]: {} },
        });
    } catch (error) {
        records.splice(0, records.length, ...originalOrder);
        throw error;
    }
}
