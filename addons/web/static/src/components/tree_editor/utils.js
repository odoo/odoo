// @ts-check

/** @module @web/components/tree_editor/utils - Shared helpers for value disambiguation, ID checking, model resolution, and default paths */

/** @import { Value } from "./condition_tree" */

/**
 * Determine whether a value is ambiguous and needs explicit typing.
 * Returns true when a value mixes strings/IDs with other types or contains empty strings.
 * @param {Value} value
 * @param {boolean} [displayNames] - whether IDs should be treated as strings
 * @returns {boolean}
 */
export function disambiguate(value, displayNames) {
    if (!Array.isArray(value)) {
        return value === "";
    }
    let hasSomeString = false;
    let hasSomethingElse = false;
    for (const val of value) {
        if (val === "") {
            return true;
        }
        if (typeof val === "string" || (displayNames && isId(val))) {
            hasSomeString = true;
        } else {
            hasSomethingElse = true;
        }
    }
    return hasSomeString && hasSomethingElse;
}

/**
 * @param {unknown} value
 * @returns {boolean} whether the value is a positive integer (valid record ID)
 */
export function isId(value) {
    return Number.isInteger(value) && value >= 1;
}

/**
 * Extract the related model name from a field definition.
 * @param {Object|null} fieldDef
 * @returns {string|null}
 */
export function getResModel(fieldDef) {
    if (fieldDef) {
        return fieldDef.is_property ? fieldDef.comodel : fieldDef.relation;
    }
    return null;
}

/** @type {string[]} */
const SPECIAL_FIELDS = ["country_id", "user_id", "partner_id", "stage_id", "id"];

/**
 * Pick a sensible default field path from a set of field definitions.
 * Prefers well-known relational fields, falls back to the first available field.
 * @param {Record<string, Object>} fieldDefs
 * @returns {string}
 * @throws {Error} if no fields exist
 */
export function getDefaultPath(fieldDefs) {
    for (const name of SPECIAL_FIELDS) {
        const fieldDef = fieldDefs[name];
        if (fieldDef) {
            return fieldDef.name;
        }
    }
    const name = Object.keys(fieldDefs)[0];
    if (name) {
        return name;
    }
    throw new Error(`No field found`);
}
