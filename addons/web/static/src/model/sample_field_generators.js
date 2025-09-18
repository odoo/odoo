// @ts-check

/** @module @web/model/sample_field_generators - Pure functions generating realistic fake field values by type */

import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";

import {
    DATE_DELTA,
    DESCRIPTION_REGEX,
    EMAIL_REGEX,
    FLOAT_PRECISION,
    getSampleFromId,
    MAX_COLOR_INT,
    MAX_FLOAT,
    MAX_INTEGER,
    MAX_MONETARY,
    PEOPLE_MODELS,
    PHONE_REGEX,
    SAMPLE_COUNTRIES,
    SAMPLE_PEOPLE,
    SAMPLE_TEXTS,
    SUB_RECORDSET_SIZE,
    URL_REGEX,
} from "./sample_data";

// ─── Random primitives ──────────────────────────────────────────────────────

/** @param {any[]} array */
export function getRandomArrayEl(array) {
    return array[Math.floor(Math.random() * array.length)];
}

/** @returns {boolean} */
export function getRandomBool() {
    return Math.random() < 0.5;
}

/** @returns {any} Luxon DateTime near today (±60 days) */
export function getRandomDate() {
    const delta = Math.floor((Math.random() - Math.random()) * DATE_DELTA);
    return luxon.DateTime.local().plus({ hours: delta });
}

/**
 * @param {number} max
 * @returns {number} float in [0, max)
 */
export function getRandomFloat(max) {
    return sanitizeNumber(Math.random() * max);
}

/**
 * @param {number} max
 * @returns {number} int in [0, max)
 */
export function getRandomInt(max) {
    return Math.floor(Math.random() * max);
}

/**
 * @param {{ selection: [string | number, string][] }} field
 * @returns {string | number | false}
 */
export function getRandomSelectionValue(field) {
    if (field.selection.length > 0) {
        return getRandomArrayEl(field.selection)[0];
    }
    return false;
}

/** @returns {number} id in [1, SUB_RECORDSET_SIZE] */
export function getRandomSubRecordId() {
    return Math.floor(Math.random() * SUB_RECORDSET_SIZE) + 1;
}

/**
 * Round to configured float precision.
 * @param {number} value
 * @returns {number}
 */
export function sanitizeNumber(value) {
    return parseFloat(value.toFixed(FLOAT_PRECISION));
}

// ─── Field value generation ─────────────────────────────────────────────────

/**
 * Generate a realistic fake value for one field based on its type and name.
 *
 * @param {string} modelName
 * @param {string} fieldName
 * @param {Record<string, any>} field - field definition (type, relation, selection, etc.)
 * @param {number} id - the record id (used for deterministic cycling)
 * @returns {any}
 */
export function generateFieldValue(modelName, fieldName, field, id) {
    switch (field.type) {
        case "boolean":
            return fieldName === "active" ? true : getRandomBool();
        case "char":
        case "text":
            return _generateTextValue(modelName, fieldName, id);
        case "date":
        case "datetime": {
            const datetime = getRandomDate();
            return field.type === "date"
                ? serializeDate(datetime)
                : serializeDateTime(datetime);
        }
        case "float":
            return getRandomFloat(MAX_FLOAT);
        case "integer": {
            let max = MAX_INTEGER;
            if (fieldName.includes("color")) {
                max = getRandomBool() ? MAX_COLOR_INT : 0;
            }
            return getRandomInt(max);
        }
        case "monetary":
            return getRandomInt(MAX_MONETARY);
        case "many2one":
            if (field.relation === "res.currency") {
                /** @todo return session.company_currency_id */
                return 1;
            }
            if (field.relation === "ir.attachment") {
                return false;
            }
            return getRandomSubRecordId();
        case "one2many":
        case "many2many": {
            const ids = [getRandomSubRecordId(), getRandomSubRecordId()];
            return [...new Set(ids)];
        }
        case "selection":
            return getRandomSelectionValue(field);
        default:
            return false;
    }
}

/**
 * Generate text/char field value based on field name heuristics.
 * @param {string} modelName
 * @param {string} fieldName
 * @param {number} id
 * @returns {string | false}
 */
function _generateTextValue(modelName, fieldName, id) {
    if (["display_name", "name"].includes(fieldName)) {
        if (PEOPLE_MODELS.includes(modelName)) {
            return getSampleFromId(id, SAMPLE_PEOPLE);
        } else if (modelName === "res.country") {
            return getSampleFromId(id, SAMPLE_COUNTRIES);
        }
    }
    if (fieldName === "display_name") {
        return getSampleFromId(id, SAMPLE_TEXTS);
    } else if (["name", "reference"].includes(fieldName)) {
        return `REF${String(id).padStart(4, "0")}`;
    } else if (DESCRIPTION_REGEX.test(fieldName)) {
        return getSampleFromId(id, SAMPLE_TEXTS);
    } else if (EMAIL_REGEX.test(fieldName)) {
        const emailName = getSampleFromId(id, SAMPLE_PEOPLE)
            .replace(/ /, ".")
            .toLowerCase();
        return `${emailName}@sample.demo`;
    } else if (PHONE_REGEX.test(fieldName)) {
        return `+1 555 754 ${String(id).padStart(4, "0")}`;
    } else if (URL_REGEX.test(fieldName)) {
        return `http://sample${id}.com`;
    }
    return false;
}
