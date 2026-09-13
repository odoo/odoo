// @ts-check
/** @odoo-module native */

import { x2ManyCommands } from "@web/core/network/commands";

/** @import { DatapointId } from "@web/model/types" */

/** @import { RelationalRecord } from "./record.js" */

/**
 * @param {RelationalRecord} record
 * @returns {DatapointId}
 */
export function listId(record) {
    return /** @type {DatapointId} */ (record.resId || record.virtualId);
}

/**
 * @param {any} value
 * @param {string} fieldType
 * @returns {any}
 */
function getSortValue(value, fieldType) {
    if (fieldType === "many2one") {
        return value ? value.display_name : "";
    }
    if (fieldType === "integer" || fieldType === "float" || fieldType === "monetary") {
        return value ?? 0;
    }
    // An unset selection is false, unlike char values deserialized to "".
    // Comparing false with nonnumeric strings makes both directions false,
    // incorrectly tying the unset value with every option.
    if (fieldType === "selection" && value === false) {
        return "";
    }
    return value ?? "";
}

/**
 * @param {Object} r1
 * @param {Object} r2
 * @param {import("@web/core/utils/order_by").OrderTerm[]} orderBy
 * @param {Object} fields
 * @returns {number}
 */
export function compareRecords(r1, r2, orderBy, fields) {
    for (const { name, asc } of orderBy) {
        const type = fields[name].type;
        const v1 = getSortValue(name === "id" ? r1.resId : r1.data[name], type);
        const v2 = getSortValue(name === "id" ? r2.resId : r2.data[name], type);
        if (v1 < v2) {
            return asc ? -1 : 1;
        }
        if (v2 < v1) {
            return asc ? 1 : -1;
        }
    }
    return 0;
}

/**
 * @param {string} fieldName
 * @param {import("@web/core/utils/order_by").OrderTerm[]} currentOrderBy
 * @param {boolean} needsReordering
 * @param {Object} [options]
 * @param {import("@web/core/utils/order_by").OrderTerm[]} [options.resetOrderBy]
 * @returns {import("@web/core/utils/order_by").OrderTerm[]}
 */
export function computeNextOrderBy(
    fieldName,
    currentOrderBy,
    needsReordering,
    { resetOrderBy = [{ name: "id", asc: true }] } = {},
) {
    let orderBy = [...currentOrderBy];
    if (fieldName) {
        if (orderBy.length && orderBy[0].name === fieldName) {
            if (!needsReordering) {
                if (orderBy[0].asc) {
                    orderBy[0] = { name: orderBy[0].name, asc: false };
                } else {
                    orderBy = [...resetOrderBy];
                }
            }
        } else {
            orderBy = orderBy.filter((o) => o.name !== fieldName);
            orderBy.unshift({
                name: fieldName,
                asc: true,
            });
        }
    }
    return orderBy;
}

/**
 * @param {Object} record
 * @param {string[]} [copyFields=[]]
 * @returns {Object}
 */
export function copyRecordData(record, copyFields = []) {
    const data = {};
    for (const [name, value] of Object.entries(record.data)) {
        if (
            ![...copyFields, "display_name"].includes(name) &&
            (record.isFieldReadonly(name) || record.isFieldInvisible(name)) &&
            !record.isFieldRequired(name)
        ) {
            continue;
        }
        switch (record.fields[name].type) {
            case "many2many": {
                const list = record.data[name];
                data[name] = list.currentIds.map((id) => {
                    const cachedRecord = list._cache.get(id);
                    const cached = cachedRecord ? copyRecordData(cachedRecord) : false;
                    return [x2ManyCommands.LINK, id, cached];
                });
                break;
            }
            case "many2one":
            case "many2one_reference":
            case "reference":
                data[name] = value && { ...value };
                break;
            case "one2many":
                break;
            default:
                data[name] = value;
        }
    }
    return data;
}

/**
 * @param {(number|string)[]} createVirtualIds
 * @param {number[]} newResIds
 * @param {{ clientIds: (number|string)[], serverIds: number[] }} [positions]
 * @returns {Map<number|string, number> | null}
 */
export function pairCreatedRows(createVirtualIds, newResIds, positions) {
    if (newResIds.length !== createVirtualIds.length) {
        return null;
    }
    const ranked = [...newResIds].sort((x, y) => x - y);
    const pairs = new Map(
        createVirtualIds.map((virtualId, index) => [virtualId, ranked[index]]),
    );
    if (positions && pairs.size) {
        const { clientIds, serverIds } = positions;
        const unmatched = new Set(pairs.keys());
        for (let index = 0; index < clientIds.length; index++) {
            const virtualId = clientIds[index];
            if (!unmatched.delete(virtualId)) {
                continue;
            }
            if (serverIds[index] !== pairs.get(virtualId)) {
                return null;
            }
            if (!unmatched.size) {
                return pairs;
            }
        }
        // Missing positions are not evidence of identity, even when both
        // memberships omit the row. Every proposed pair must be witnessed.
        return null;
    }
    return pairs;
}
