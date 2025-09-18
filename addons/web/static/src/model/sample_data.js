// @ts-check

/** @module @web/model/sample_data - Sample data constants and text arrays for fake record generation */

// ─── Recordset sizes ────────────────────────────────────────────────────────
export const MAIN_RECORDSET_SIZE = 16;
export const SUB_RECORDSET_SIZE = 5;
export const SEARCH_READ_LIMIT = 10;
export const MAX_NUMBER_OPENED_GROUPS = 10;

// ─── Numeric limits ─────────────────────────────────────────────────────────
export const MAX_FLOAT = 100;
export const MAX_INTEGER = 50;
export const MAX_COLOR_INT = 7;
export const MAX_MONETARY = 100000;
/** Delta in hours — spread across 60 days. */
export const DATE_DELTA = 24 * 60;
export const FLOAT_PRECISION = 2;

// ─── Date formats ───────────────────────────────────────────────────────────
/** @type {Record<string, string>} */
export const FORMATS = {
    day: "yyyy-MM-dd",
    week: "'W'WW kkkk",
    month: "MMMM yyyy",
    quarter: "'Q'q yyyy",
    year: "y",
};
/** @type {Record<string, (dt: any) => any>} */
export const INTERVALS = {
    day: (dt) => dt.plus({ days: 1 }),
    week: (dt) => dt.plus({ weeks: 1 }),
    month: (dt) => dt.plus({ months: 1 }),
    quarter: (dt) => dt.plus({ months: 3 }),
    year: (dt) => dt.plus({ years: 1 }),
};
export const DISPLAY_FORMATS = { ...FORMATS, day: "dd MMM yyyy" };

// ─── Sample text arrays ─────────────────────────────────────────────────────
/** @type {string[]} */
export const SAMPLE_COUNTRIES = [
    "Belgium",
    "France",
    "Portugal",
    "Singapore",
    "Australia",
];
/** @type {string[]} */
export const SAMPLE_PEOPLE = [
    "John Miller",
    "Henry Campbell",
    "Carrie Helle",
    "Wendi Baltz",
    "Thomas Passot",
];
/** @type {string[]} */
export const SAMPLE_TEXTS = [
    "Laoreet id",
    "Volutpat blandit",
    "Integer vitae",
    "Viverra nam",
    "In massa",
];
/** @type {string[]} */
export const PEOPLE_MODELS = [
    "res.users",
    "res.partner",
    "hr.employee",
    "mail.followers",
    "mailing.contact",
];

// ─── Field name regex patterns ──────────────────────────────────────────────
/**
 * Returns a regex matching a term as a word boundary in a field name.
 * `fieldNameRegex('abc')` matches "abc", "field_abc__def" but not "aabc".
 * @param {...string} terms
 * @returns {RegExp}
 */
export function fieldNameRegex(...terms) {
    return new RegExp(`\\b((\\w+)?_)?(${terms.join("|")})(_(\\w+)?)?\\b`);
}

export const MEASURE_SPEC_REGEX = /(?<fieldName>\w+):(?<func>\w+)/;
export const DESCRIPTION_REGEX = fieldNameRegex(
    "description",
    "label",
    "title",
    "subject",
    "message",
);
export const EMAIL_REGEX = fieldNameRegex("email");
export const PHONE_REGEX = fieldNameRegex("phone");
export const URL_REGEX = fieldNameRegex("url");

// ─── Helpers ────────────────────────────────────────────────────────────────
/**
 * Returns the sample value corresponding to a record ID (cyclic).
 * @param {number} id
 * @param {any[]} sampleTexts
 * @returns {any}
 */
export function getSampleFromId(id, sampleTexts) {
    return sampleTexts[(id - 1) % sampleTexts.length];
}
