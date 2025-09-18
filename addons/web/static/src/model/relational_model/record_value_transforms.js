// @ts-check

/** @module @web/model/relational_model/record_value_transforms - Stateless value formatting, defaults, and eval context extraction */

/**
 * Pure value transformation functions for Record data.
 *
 * Handles formatting JS field values back to server format, computing default
 * values for empty fields, extracting text values for char/text/html fields,
 * and building eval contexts from record data.
 *
 * These are stateless — they depend only on their arguments, making them
 * independently testable and reusable outside of a Record instance.
 */

/**
 * Format a JS field value back to server format.
 *
 * Inverse of `parseServerValue` (in utils.js). Handles all field types
 * including recursive property definitions.
 *
 * @param {string} fieldType
 * @param {any} value
 * @returns {any} server-formatted value
 */

import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
export function formatServerValue(fieldType, value) {
    switch (fieldType) {
        case "date":
            return value ? serializeDate(value) : false;
        case "datetime":
            return value ? serializeDateTime(value) : false;
        case "char":
        case "text":
            return value !== "" ? value : false;
        case "html":
            return value?.length ? value : false;
        case "many2one":
            return value ? value.id : false;
        case "many2one_reference":
            return value ? value.resId : 0;
        case "reference":
            return value?.resModel && value.resId
                ? `${value.resModel},${value.resId}`
                : false;
        case "properties":
            return value.map((property) => {
                property = { ...property };
                for (const key of ["value", "default"]) {
                    let val;
                    if (property.type === "many2one") {
                        val = property[key] && [
                            property[key].id,
                            property[key].display_name,
                        ];
                    } else if (
                        (property.type === "date" || property.type === "datetime") &&
                        typeof property[key] === "string"
                    ) {
                        // TO REMOVE: need refactoring PropertyField to use the same format as the server
                        val = property[key];
                    } else if (property[key] !== undefined) {
                        val = formatServerValue(property.type, property[key]);
                    }
                    property[key] = val;
                }
                return property;
            });
        default:
            return value;
    }
}

/**
 * Compute default values for fields that don't have data yet.
 *
 * @param {string[]} fieldNames
 * @param {Object} fields - field definitions
 * @returns {Object} default values keyed by field name
 */
export function getDefaultValues(fieldNames, fields) {
    const defaultValues = {};
    for (const fieldName of fieldNames) {
        switch (fields[fieldName].type) {
            case "integer":
            case "float":
            case "monetary":
                defaultValues[fieldName] = fieldName === "id" ? false : 0;
                break;
            case "one2many":
            case "many2many":
                defaultValues[fieldName] = [];
                break;
            default:
                defaultValues[fieldName] = false;
        }
    }
    return defaultValues;
}

/**
 * Extract text values for char, text, and html fields.
 *
 * These track the raw server values so the eval context distinguishes
 * between NULL (false) and empty string ("") for char/text/html fields.
 *
 * @param {Object} values - field values
 * @param {Object} activeFields
 * @param {Object} fields - field definitions
 * @returns {Object} text values keyed by field name
 */
export function getTextValues(values, activeFields, fields) {
    const textValues = {};
    for (const fieldName in values) {
        if (!activeFields[fieldName]) {
            continue;
        }
        if (["char", "text", "html"].includes(fields[fieldName].type)) {
            textValues[fieldName] = values[fieldName];
        }
    }
    return textValues;
}

/**
 * Build a data context suitable for Python eval expressions from record data.
 *
 * Returns two variants: one including virtual IDs (for attribute evaluation)
 * and one with only real database IDs (for server-bound contexts).
 *
 * @param {Object} data - record data (should be toRaw'd before passing)
 * @param {Object} fields - field definitions
 * @param {Object} textValues - text values for char/text/html fields
 * @param {number|false} resId
 * @returns {{ withVirtualIds: Object, withoutVirtualIds: Object }}
 */
export function computeDataContext(data, fields, textValues, resId) {
    const dataContext = {};
    const x2manyDataContext = {
        withVirtualIds: {},
        withoutVirtualIds: {},
    };
    for (const fieldName in data) {
        const value = data[fieldName];
        const field = fields[fieldName];
        if (field.relatedPropertyField) {
            continue;
        }
        if (["char", "text", "html"].includes(field.type)) {
            dataContext[fieldName] = textValues[fieldName];
        } else if (field.type === "one2many" || field.type === "many2many") {
            x2manyDataContext.withVirtualIds[fieldName] = value.currentIds;
            x2manyDataContext.withoutVirtualIds[fieldName] = value.currentIds.filter(
                (id) => typeof id === "number",
            );
        } else if (value && field.type === "date") {
            dataContext[fieldName] = serializeDate(value);
        } else if (value && field.type === "datetime") {
            dataContext[fieldName] = serializeDateTime(value);
        } else if (value && field.type === "many2one") {
            dataContext[fieldName] = value.id;
        } else if (value && field.type === "reference") {
            dataContext[fieldName] = `${value.resModel},${value.resId}`;
        } else if (field.type === "properties") {
            dataContext[fieldName] = value.filter(
                (property) => !property.definition_deleted,
            );
        } else {
            dataContext[fieldName] = value;
        }
    }
    dataContext.id = resId || false;
    return {
        withVirtualIds: { ...dataContext, ...x2manyDataContext.withVirtualIds },
        withoutVirtualIds: {
            ...dataContext,
            ...x2manyDataContext.withoutVirtualIds,
        },
    };
}
