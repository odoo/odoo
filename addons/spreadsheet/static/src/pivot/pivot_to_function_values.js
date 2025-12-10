import { registries, helpers, constants } from "@odoo/o-spreadsheet";

const { DEFAULT_LOCALE } = constants;
const { pivotToFunctionValueRegistry } = registries;
const { toString, toNumber } = helpers;

/**
 * Add pivot formatting functions to support odoo specific fields
 * in spreadsheet
 */

const toFunctionValueDateTime = pivotToFunctionValueRegistry.get("date");

function isFalseValue(value) {
    return value === false || (typeof value === "string" && value.toLowerCase() === "false");
}

function _toDate(value, granularity) {
    if (isFalseValue(value)) {
        return "FALSE";
    }
    if (!granularity) {
        granularity = "month";
    }
    return toFunctionValueDateTime(value, granularity);
}

function _toString(value) {
    if (isFalseValue(value)) {
        return "FALSE";
    }
    return `"${toString(value).replace(/"/g, '\\"')}"`;
}
function _toNumber(value) {
    if (isFalseValue(value)) {
        return "FALSE";
    }
    return `${toNumber(value, DEFAULT_LOCALE)}`;
}

pivotToFunctionValueRegistry
    .add("text", _toString)
    .add("selection", _toString)
    .replace("char", _toString)
    .replace("integer", _toNumber)
    .add("reference", _toString)
    .add("monetary", _toNumber)
    .add("many2one", _toNumber)
    .add("many2one_reference", _toNumber)
    .add("many2many", _toNumber)
    .add("float", _toNumber)
    .replace("date", _toDate)
    .replace("datetime", _toDate);
