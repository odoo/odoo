// @ts-check

/** @module @web/views/pivot/pivot_value_utils - GroupBy normalization, value sanitization, and header cell computation for the pivot model */

/**
 * Normalize a groupBy specification, adding default interval for date fields.
 *
 * @param {string} gb
 * @param {Object} fields
 * @returns {string}
 */

import { _t } from "@web/core/l10n/translation";
function normalize(gb, fields) {
    const [fieldName, interval] = gb.split(":");
    const field = fields[fieldName];
    if (["date", "datetime"].includes(field.type)) {
        return `${fieldName}:${interval || "month"}`;
    }
    return fieldName;
}

/**
 * Extract from a groupBy value the raw value (discarding a label if any).
 *
 * @param {any} value
 * @returns {any}
 */
function sanitizeValue(value) {
    if (Array.isArray(value)) {
        return value[0];
    }
    return value;
}

/**
 * Extract from a groupBy value a display label.
 *
 * @param {any} value
 * @param {string} groupBy
 * @param {Object} config
 * @returns {string}
 */
function sanitizeLabel(value, groupBy, config) {
    const { metaData } = config;
    const fieldName = groupBy.split(":")[0];
    if (fieldName && metaData.fields[fieldName]) {
        const field = metaData.fields[fieldName];
        if (field.type === "boolean") {
            return value === undefined ? _t("None") : value ? _t("Yes") : _t("No");
        } else if (field.type === "integer") {
            if (fieldName === "id" && Array.isArray(value)) {
                return value[1];
            }
            return value || "0";
        }
    }
    if (value === false) {
        return metaData.fields[fieldName].falsy_value_label || _t("None");
    }
    if (Array.isArray(value)) {
        return getNumberedLabel(value, fieldName, config);
    }
    if (
        fieldName &&
        metaData.fields[fieldName] &&
        metaData.fields[fieldName].type === "selection"
    ) {
        const selected = metaData.fields[fieldName].selection.find(
            (o) => o[0] === value,
        );
        return selected ? selected[1] : value;
    }
    return value;
}

/**
 * Make sure that the labels of different many2one values are distinguished
 * by numbering them if necessary.
 *
 * @param {Array} label
 * @param {string} fieldName
 * @param {Object} config
 * @returns {string}
 */
function getNumberedLabel(label, fieldName, config) {
    const { data } = config;
    const id = label[0];
    const name = label[1];
    data.numbering[fieldName] = data.numbering[fieldName] || {};
    data.numbering[fieldName][name] = data.numbering[fieldName][name] || {};
    const numbers = data.numbering[fieldName][name];
    numbers[id] = numbers[id] || Object.keys(numbers).length + 1;
    return numbers[id] > 1 ? `${name}  (${numbers[id]})` : name;
}

/**
 * Returns the group sanitized labels.
 *
 * @param {Object} group
 * @param {string[]} groupBys
 * @param {Object} config
 * @param {Object} fields
 * @returns {string[]}
 */
export function getGroupLabels(group, groupBys, config, fields) {
    return groupBys.map((gb) => {
        const groupBy = normalize(gb, fields);
        return sanitizeLabel(group[groupBy], groupBy, config);
    });
}

/**
 * Returns the group sanitized values.
 *
 * @param {Object} group
 * @param {string[]} groupBys
 * @param {Object} fields
 * @returns {Array}
 */
export function getGroupValues(group, groupBys, fields) {
    return groupBys.map((gb) => {
        const groupBy = normalize(gb, fields);
        return sanitizeValue(group[groupBy]);
    });
}

/**
 * Deduplicate and merge row and col groupBy specifications.
 *
 * @param {string[]} rowGroupBy
 * @param {string[]} colGroupBy
 * @param {Object} fields
 * @returns {string[]}
 */
export function getGroupBySpecs(rowGroupBy, colGroupBy, fields) {
    const set = [...rowGroupBy, ...colGroupBy].reduce((acc, gb) => {
        acc.add(normalize(gb, fields));
        return acc;
    }, new Set());
    return [...set];
}

/**
 * Returns a domain representation of a group.
 *
 * @param {Object} group
 * @param {Object} config
 * @returns {Array[]}
 */
export function getGroupDomain(group, config) {
    const { data } = config;
    const key = JSON.stringify([group.rowValues, group.colValues]);
    return data.groupDomains[key];
}
