import { makeErrorFromResponse } from "@web/core/network/rpc";

/**
 * @typedef {{
 *  code?: number;
 *  context?: import("@web/core/context").Context;
 *  description?: string;
 *  message?: string;
 *  subType?: string;
 *  errorName?: string;
 *  type?: string;
 *  args?: unknown[];
 * }} ServerErrorInit
 */

/**
 * @template T
 * @typedef {import("./mock_server").KwArgs<T>} KwArgs
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * This is a flag on keyword arguments, so that they can easily be distinguished
 * from args in ORM methods. They can then be easily retrieved with {@link getKwArgs}.
 */
const KWARGS_SYMBOL = Symbol("is_kwargs");

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Flags keyword arguments, so that they can easily be distinguished from regular
 * arguments in ORM methods.
 *
 * They can then be easily retrieved with {@link getKwArgs}.
 *
 * @template T
 * @param {T} kwargs
 * @returns {T}
 */
export function makeKwArgs(kwargs) {
    kwargs[KWARGS_SYMBOL] = true;
    return kwargs;
}

/**
 * Retrieves keyword arguments flagged by {@link makeKwArgs} from an arguments list.
 *
 * @template {string} T
 * @param {Iterable<any>} allArgs arguments of method
 * @param  {...T} argNames ordered names of positional arguments
 * @returns {KwArgs<Record<T, any>>} kwargs normalized params
 */
export function getKwArgs(allArgs, ...argNames) {
    const args = [...allArgs];
    const kwargs = args.at(-1)?.[KWARGS_SYMBOL] ? args.pop() : makeKwArgs({});
    if (args.length > argNames.length) {
        throw new MockServerError("More positional arguments than there are given argument names");
    }
    for (let i = 0; i < args.length; i++) {
        if (args[i] !== null && args[i] !== undefined) {
            kwargs[argNames[i]] = args[i];
        }
    }
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
 * @param {ServerErrorInit} params
 */
export function makeServerError({
    code,
    context,
    description,
    message,
    subType,
    errorName,
    type,
    args,
} = {}) {
    return makeErrorFromResponse({
        code: code || 0,
        data: {
            name: errorName || `odoo.exceptions.${type || "UserError"}`,
            debug: "traceback",
            arguments: args || [],
            context: context || {},
            subType,
            message: description || message,
        },
        message: message || "Odoo Server Error",
        type: "server",
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

/**
 * Removes the flag for keyword arguments.
 *
 * @template T
 * @param {T} kwargs
 * @returns {T}
 */
export function unmakeKwArgs(kwargs) {
    delete kwargs[KWARGS_SYMBOL];
    return kwargs;
}

export class MockServerError extends Error {
    name = "MockServerError";
}
