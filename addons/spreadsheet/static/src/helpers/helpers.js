/** @odoo-module */

import spreadsheet from "../o_spreadsheet/o_spreadsheet_extended";
import { DataSources } from "../data_sources/data_sources";
import { serializeDate } from "@web/core/l10n/dates";
import { migrate } from "@spreadsheet/o_spreadsheet/migration";
import { loadJS } from "@web/core/assets";

const { DateTime } = luxon;

const Model = spreadsheet.Model;

/**
 * Get the intersection of two arrays
 *
 * @param {Array} a
 * @param {Array} b
 *
 * @private
 * @returns {Array} intersection between a and b
 */
export function intersect(a, b) {
    return a.filter((x) => b.includes(x));
}

/**
 * Given an object of form {"1": {...}, "2": {...}, ...} get the maximum ID used
 * in this object
 * If the object has no keys, return 0
 *
 * @param {Object} o an object for which the keys are an ID
 *
 * @returns {number}
 */
export function getMaxObjectId(o) {
    const keys = Object.keys(o);
    if (!keys.length) {
        return 0;
    }
    const nums = keys.map((id) => parseInt(id, 10));
    const max = Math.max(...nums);
    return max;
}

/**
 * see https://stackoverflow.com/a/30106551
 * @param {string} string
 * @returns {string}
 */
function utf8ToBase64(str) {
    // first we use encodeURIComponent to get percent-encoded UTF-8,
    // then we convert the percent encodings into raw bytes which
    // can be fed into btoa.
    return btoa(
        encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, function toSolidBytes(match, p1) {
            return String.fromCharCode("0x" + p1);
        })
    );
}

/**
 * see https://stackoverflow.com/a/30106551
 * @param {string} string
 * @returns {string}
 */
function base64ToUtf8(str) {
    // Going backwards: from bytestream, to percent-encoding, to original string.
    return decodeURIComponent(
        atob(str)
            .split("")
            .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
            .join("")
    );
}

/**
 * Encode a json to a base64 string
 * @param {object} json
 */
export function jsonToBase64(json) {
    return utf8ToBase64(JSON.stringify(json));
}

/**
 * Decode a base64 encoded json
 * @param {string} string
 */
export function base64ToJson(string) {
    return JSON.parse(base64ToUtf8(string));
}

/**
 * Takes a template id as input, will convert the formulas
 * from relative to absolute in a way that they can be used to create a sheet.
 *
 * @param {Function} rpc
 * @param {number} templateId
 * @returns {Promise<Object>} spreadsheetData
 */
export async function getDataFromTemplate(env, orm, templateId) {
    let [{ data }] = await orm.read("spreadsheet.template", [templateId], ["data"]);
    data = base64ToJson(data);

    const model = new Model(migrate(data), {
        dataSources: new DataSources(orm),
    });
    await model.config.dataSources.waitForAllLoaded();
    const proms = [];
    for (const pivotId of model.getters.getPivotIds()) {
        proms.push(model.getters.getPivotDataSource(pivotId).prepareForTemplateGeneration());
    }
    await Promise.all(proms);
    model.dispatch("CONVERT_PIVOT_FROM_TEMPLATE");
    return model.exportData();
}

/** converts and orderBy Object to a string equivalent that can be processed by orm.call */
export function orderByToString(orderBy) {
    return orderBy.map((o) => `${o.name} ${o.asc ? "ASC" : "DESC"}`).join(", ");
}

/**
 * Convert a spreadsheet date representation to an odoo
 * server formatted date
 *
 * @param {Date} value
 * @returns {string}
 */
export function toServerDateString(value) {
    const date = DateTime.fromJSDate(value);
    return serializeDate(date);
}

/**
 * @param {number[]} array
 * @returns {number}
 */
export function sum(array) {
    return array.reduce((acc, n) => acc + n, 0);
}

function camelToSnakeKey(word) {
    const result = word.replace(/(.){1}([A-Z])/g, "$1 $2");
    return result.split(" ").join("_").toLowerCase();
}

/**
 * Recursively convert camel case object keys to snake case keys
 * @param {object} obj
 * @returns {object}
 */
export function camelToSnakeObject(obj) {
    const result = {};
    for (const [key, value] of Object.entries(obj)) {
        const isPojo = typeof value === "object" && value !== null && value.constructor === Object;
        result[camelToSnakeKey(key)] = isPojo ? camelToSnakeObject(value) : value;
    }
    return result;
}

/**
 * Check if the argument is falsy or is an empty object/array
 *
 * TODO : remove this and replace it by the one in o_spreadsheet xlsx import when its merged
 */
export function isEmpty(item) {
    if (!item) {
        return true;
    }
    if (typeof item === "object") {
        if (
            Object.values(item).length === 0 ||
            Object.values(item).every((val) => val === undefined)
        ) {
            return true;
        }
    }
    return false;
}

/**
 * Load external libraries required for o-spreadsheet
 * @returns {Promise<void>}
 */
export async function loadSpreadsheetDependencies() {
    await loadJS("/web/static/lib/Chart/Chart.js");
    // chartjs-gauge should only be loaded when Chart.js is fully loaded !
    await loadJS("/spreadsheet/static/lib/chartjs-gauge/chartjs-gauge.js");
}
