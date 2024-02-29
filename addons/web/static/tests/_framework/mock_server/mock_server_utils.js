import { makeErrorFromResponse } from "@web/core/network/rpc";

/**
 * flag kwargs, so that they can model methods can be easily parsed to combine args/kwargs like in python
 * @see parseModelParams
 */
const IS_KWARGS = Symbol("is_kwargs");
export function isKwargs(kwargs) {
    return kwargs?.[IS_KWARGS];
}
export function Kwargs(obj) {
    obj[IS_KWARGS] = true;
    return obj;
}

/**
 * @param {import("./mock_model").ModelRecord} record
 */
export function getRecordQualifier(record) {
    if (record.id) {
        return `record #${record.id}`;
    }
    const name = record.display_name || record.name;
    if (name) {
        return `record named "${name}"`;
    }
    return "anonymous record";
}

/**
 * @param {Record<string, string | any>} params
 */
export function makeServerError({ code, context, description, message, subType, type } = {}) {
    return makeErrorFromResponse({
        code: code || 200,
        message: message || "Odoo Server Error",
        data: {
            name: `odoo.exceptions.${type || "UserError"}`,
            debug: "traceback",
            arguments: [],
            context: context || {},
            subType,
            message: description,
        },
    });
}

/**
 * @param {unknown} value
 * @param {string} [separator=","]
 */
export function safeSplit(value, separator) {
    return value
        ? String(value)
              .trim()
              .split(separator || ",")
        : [];
}

export class MockServerError extends Error {
    name = "MockServerError";
}

export const FIELD_NOT_FOUND = Symbol("FIELD_NOT_FOUND");
