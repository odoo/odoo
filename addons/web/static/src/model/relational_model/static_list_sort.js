// @ts-check
/** @odoo-module native */

import { pick } from "@web/core/utils/collections/objects";

import { parseServerValue } from "./field_values.js";
import { computeResequencePlan } from "./resequence.js";
import { compareRecords, computeNextOrderBy } from "./static_list_utils.js";

/** @import { StaticList } from "@web/model/relational_model/static_list" */

/**
 * @typedef {Pick<StaticList, "currentIds" | "_currentIds" | "orderBy" | "_needsReordering" | "fieldNames" | "fields" | "activeFields" | "config" | "evalContext" | "_getResIdsToLoad" | "loadLocked" | "markReordered"> & {
 * model: Pick<StaticList["model"], "loadRecords">;
 * _cache: Map<import("@web/model/types").DatapointId, Pick<import("./record").RelationalRecord, "resId" | "data" | "applyValues">>;
 * _createRecordDatapoint: (data: Record<string, any>) => void;
 * }} SortableList
 */

/**
 * @param {SortableList} list
 * @param {any[]} [currentIds]
 * @param {any[]} [orderBy]
 */
export async function sortStaticList(
    list,
    currentIds = list.currentIds,
    orderBy = list.orderBy,
) {
    if (!orderBy.length) {
        return currentIds;
    }
    const fieldNames = orderBy.map((o) => o.name);
    /** @type {Map<any, { resId: any, data: Record<string, any> }>} */
    const sortKeys = new Map();
    const resIds = list._getResIdsToLoad(currentIds, fieldNames);
    if (resIds.length) {
        const activeFields = pick(list.activeFields, ...fieldNames);
        const sortSpecIsTotal = list.fieldNames.every((name) =>
            Object.hasOwn(activeFields, name),
        );
        const config = { ...list.config, resIds, activeFields };
        const records = await list.model.loadRecords(config, list.evalContext);
        for (const record of records) {
            const cached = list._cache.get(record.id);
            if (cached) {
                cached.applyValues(record);
                continue;
            }
            if (sortSpecIsTotal) {
                list._createRecordDatapoint(record);
                continue;
            }
            /** @type {Record<string, any>} */
            const data = {};
            for (const name of fieldNames) {
                if (name in record) {
                    data[name] = parseServerValue(list.fields[name], record[name]);
                }
            }
            sortKeys.set(record.id, { resId: record.id, data });
        }
    }
    const cache = list._cache;
    const sortableOf = (/** @type {any} */ id) => cache.get(id) || sortKeys.get(id);
    const entries = currentIds
        .filter((/** @type {any} */ id) => sortableOf(id))
        .map((/** @type {any} */ id) => ({ id, sortable: sortableOf(id) }));
    entries.sort((a, b) =>
        compareRecords(a.sortable, b.sortable, orderBy, list.fields),
    );
    await list.loadLocked({
        orderBy,
        nextCurrentIds: entries.map((e) => e.id),
    });
    list.markReordered();
}

/**
 * @param {StaticList} staticList
 * @param {number|string} movedId
 * @param {number|string|null} targetId
 */
export async function resequenceStaticList(staticList, movedId, targetId) {
    const handleField = /** @type {string} */ (staticList.handleField);
    const order = staticList.orderBy.find((o) => o.name === handleField);
    const asc = !order || order.asc;

    const { toReorder, offset } = computeResequencePlan({
        records: staticList.records,
        movedId,
        targetId,
        getSequence: (rec) => rec?.data[handleField],
        asc,
    });

    if (!toReorder.length) {
        return;
    }

    const proms = [];
    for (const [i, record] of Object.entries(toReorder)) {
        proms.push(
            record.updateLocked(
                { [handleField]: offset + Number(i) },
                { withoutParentUpdate: true },
            ),
        );
    }
    await Promise.all(proms);

    await sortStaticList(staticList);
    await staticList.notifyParentUpdate();
}

/**
 * @param {SortableList} list
 * @param {string} fieldName
 */
export function sortBy(list, fieldName) {
    const orderBy = computeNextOrderBy(
        fieldName,
        list.orderBy,
        Boolean(list._needsReordering),
    );
    return sortStaticList(list, list._currentIds, orderBy);
}
