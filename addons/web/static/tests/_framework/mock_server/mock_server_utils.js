import { makeErrorFromResponse } from "@web/core/network/rpc";

/**
 * This is a flag on kwargs, so that they can easily be distinguished from args in methods of models.
 * That way they can be easily be parsed, e.g. by combining args & kwargs @see parseModelParams
 */
const IS_KWARGS = Symbol("is_kwargs");

/**
 * @template T
 * @param {T} kwargs
 */
export function isKwargs(kwargs) {
    return Boolean(kwargs?.[IS_KWARGS]);
}

/**
 * @template T
 * @param {T} kwargs
 * @returns {T}
 */
export function Kwargs(kwargs) {
    kwargs[IS_KWARGS] = true;
    return kwargs;
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
