// @ts-check

/** @module @web/model/relational_model/static_list_utils - Sorting comparators, record duplication, and sort-direction cycling for StaticList */

/**
 * Pure utility functions for StaticList.
 *
 * Sorting comparators, record data copying for duplication, and
 * sort-direction cycling — all stateless and independently testable.
 */

// ---------------------------------------------------------------------------
// Sorting
// ---------------------------------------------------------------------------

/**
 * Compare two field values for ordering purposes.
 * For many2one fields, compares by display_name.
 *
 * @param {any} v1
 * @param {any} v2
 * @param {string} fieldType
 * @returns {boolean} true if v1 < v2
 */

import { x2ManyCommands } from "@web/services/orm_service";

function compareFieldValues(v1, v2, fieldType) {
    if (fieldType === "many2one") {
        v1 = v1 ? v1.display_name : "";
        v2 = v2 ? v2.display_name : "";
    }
    return v1 < v2;
}

/**
 * Recursively compare two records by an ordered list of sort criteria.
 * Falls through to the next criterion on ties.
 *
 * @param {Object} r1
 * @param {Object} r2
 * @param {import("@web/core/utils/order_by").OrderTerm[]} orderBy
 * @param {Object} fields - field definitions
 * @returns {number} -1, 0, or 1
 */
export function compareRecords(r1, r2, orderBy, fields) {
    const { name, asc } = orderBy[0];
    function getValue(record, fieldName) {
        return fieldName === "id" ? record.resId : record.data[fieldName];
    }
    const v1 = asc ? getValue(r1, name) : getValue(r2, name);
    const v2 = asc ? getValue(r2, name) : getValue(r1, name);
    if (compareFieldValues(v1, v2, fields[name].type)) {
        return -1;
    }
    if (compareFieldValues(v2, v1, fields[name].type)) {
        return 1;
    }
    if (orderBy.length > 1) {
        return compareRecords(r1, r2, orderBy.slice(1), fields);
    }
    return 0;
}

/**
 * Compute the next orderBy spec after clicking a column header.
 *
 * Cycles through: asc → desc → reset (id asc).
 * If the column wasn't the primary sort, it becomes the new primary (asc).
 * If reordering is pending, the current direction is kept.
 *
 * @param {string} fieldName - column clicked
 * @param {import("@web/core/utils/order_by").OrderTerm[]} currentOrderBy
 * @param {boolean} needsReordering - true when a drag-reorder is pending
 * @returns {import("@web/core/utils/order_by").OrderTerm[]}
 */
export function computeNextOrderBy(fieldName, currentOrderBy, needsReordering) {
    let orderBy = [...currentOrderBy];
    if (fieldName) {
        if (orderBy.length && orderBy[0].name === fieldName) {
            if (!needsReordering) {
                if (orderBy[0].asc) {
                    orderBy[0] = { name: orderBy[0].name, asc: false };
                } else {
                    orderBy = [{ name: "id", asc: true }];
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

// ---------------------------------------------------------------------------
// Record copying
// ---------------------------------------------------------------------------

/**
 * Extract copyable data from a record for duplication.
 *
 * Skips readonly/invisible non-required fields (except display_name and
 * explicitly listed copyFields).  For many2many, produces LINK commands
 * with cached record data.  one2many fields are left empty (not supported).
 *
 * @param {Object} record - source Record datapoint
 * @param {string[]} [copyFields=[]] - fields to always include
 * @returns {Object} data suitable for passing to `_update`
 */
export function copyRecordData(record, copyFields = []) {
    const data = {};
    for (const [name, value] of Object.entries(record.data)) {
        if (
            ![...copyFields, "display_name"].includes(name) &&
            (record._isReadonly(name) || record._isInvisible(name)) &&
            !record._isRequired(name)
        ) {
            continue;
        }
        switch (record.fields[name].type) {
            case "many2many": {
                const list = record.data[name];
                data[name] = list.currentIds.map((id) => {
                    let data;
                    if (list._cache[id]) {
                        data = copyRecordData(list._cache[id]);
                    }
                    return [x2ManyCommands.LINK, id, data];
                });
                break;
            }
            case "many2one":
            case "many2one_reference":
            case "reference":
                data[name] = value && { ...value };
                break;
            case "one2many":
                // Not supported => that field is left empty
                break;
            default:
                data[name] = value;
        }
    }
    return data;
}
