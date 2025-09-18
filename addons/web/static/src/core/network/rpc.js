// @ts-check

/** @module @web/core/network/rpc - JSON-RPC client with error classification, request bus events, and XHR settings */

import { EventBus } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { omit } from "@web/core/utils/collections/objects";

/**
 * @typedef {{
 *  code: number;
 *  message: string;
 *  data?: unknown;
 *  type?: string;
 * }} JsonRpcError
 */

export const rpcBus = new EventBus();

const RPC_SETTINGS = new Set(["cache", "silent", "xhr", "headers"]);
/**
 * @param {{[key: string]: any}} settings
 */
function validateRPCSettings(settings) {
    const invalidKeys = Object.keys(settings).filter((key) => !RPC_SETTINGS.has(key));
    if (invalidKeys.length) {
        const invalid = invalidKeys.map((k) => `"${k}"`).join(", ");
        const valid = [...RPC_SETTINGS].map((k) => `"${k}"`).join(", ");
        throw new Error(
            `Invalid RPC setting(s): ${invalid}. Valid settings are: ${valid}`,
        );
    }
    if ("cache" in settings && "xhr" in settings) {
        throw new Error("Can't use 'cache' and 'xhr' at the same time");
    }
}

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------
export class RPCError extends Error {
    constructor(...args) {
        super(...args);
        /** @type {string} */
        this.name = "RPC_ERROR";
        /** @type {string | null} */
        this.type = "server";
        /** @type {number | null} */
        this.code = null;
        /** @type {any} */
        this.data = null;
        /** @type {string | null} */
        this.exceptionName = null;
        /** @type {string | null} */
        this.subType = null;
    }
}

export class ConnectionLostError extends Error {
    /**
     * @param {string} url
     * @param  {...any} args
     */
    constructor(url, ...args) {
        const message = url
            ? `Connection to "${url}" couldn't be established or was interrupted`
            : "Connection couldn't be established or was interrupted";
        super(message, ...args);
        /** @type {string} */
        this.url = url;
    }
}

export class ConnectionAbortedError extends Error {}

/**
 * @param {JsonRpcError} response
 * @returns {RPCError}
 */
export function makeErrorFromResponse(response) {
    // Odoo returns error like this, in a error field instead of properly
    // using http error codes...
    const { code, data: errorData, message, type: subType } = response;
    const error = new RPCError();
    error.exceptionName = /** @type {any} */ (errorData)?.name;
    error.subType = subType;
    error.data = errorData;
    error.message = message;
    error.code = code;
    return error;
}

// -----------------------------------------------------------------------------
// Cache RPC method
// -----------------------------------------------------------------------------

/** @type {any} */
let rpcCache;

rpc.setCache = function (/** @type {any} */ cache) {
    rpcCache = cache;
};

rpcBus.addEventListener("CLEAR-CACHES", (event) => {
    const detail = /** @type {any} */ (event).detail;
    if (
        detail &&
        typeof detail === "object" &&
        !Array.isArray(detail) &&
        detail.model
    ) {
        rpcCache?.invalidateByModel(detail.tables, detail.model);
    } else {
        rpcCache?.invalidate(detail);
    }
});

// -----------------------------------------------------------------------------
// Main RPC
// -----------------------------------------------------------------------------
let rpcId = 0;
/**
 * @param {string} url
 * @param {{[key: string]: any}} [params]
 * @param {{[key: string]: any}} [settings]
 * @returns {any}
 */
export function rpc(url, params = {}, settings = {}) {
    return rpc._rpc(url, params, settings);
}
// such that it can be overriden in tests
rpc._rpc = function (url, params, settings) {
    validateRPCSettings(settings);
    if (settings.cache && rpcCache) {
        return rpcCache.read(
            params?.method || url, // table
            JSON.stringify({ url, params }), // key
            () => rpc._rpc(url, params, omit(settings, "cache")),
            typeof settings.cache === "boolean" ? {} : settings.cache, // cache can be boolean or an object with options (or an empty object of course)
        );
    }
    const XHR = browser.XMLHttpRequest;
    const data = {
        id: rpcId++,
        jsonrpc: "2.0",
        method: "call",
        params: params,
    };
    const request = settings.xhr || new XHR();
    const { promise, resolve, reject } = Promise.withResolvers();
    rpcBus.trigger("RPC:REQUEST", { data, url, settings });
    // handle success
    request.addEventListener("load", () => {
        if (request.status === 502) {
            // If Odoo is behind another server (eg.: nginx)
            const error = new ConnectionLostError(url);
            rpcBus.trigger("RPC:RESPONSE", { data, settings, error });
            reject(error);
            return;
        }
        let response;
        try {
            response = JSON.parse(request.response);
        } catch {
            // the response isn't json parsable, which probably means that the rpc request could
            // not be handled by the server, e.g. PoolError('The Connection Pool Is Full')
            const error = new ConnectionLostError(url);
            rpcBus.trigger("RPC:RESPONSE", { data, settings, error });
            return reject(error);
        }
        const { error: responseError, result: responseResult } = response;
        if (!response.error) {
            rpcBus.trigger("RPC:RESPONSE", {
                data,
                settings,
                result: response.result,
            });
            return resolve(responseResult);
        }
        const error = makeErrorFromResponse(responseError);
        /** @type {any} */ (error).model = data.params.model;
        rpcBus.trigger("RPC:RESPONSE", { data, settings, error });
        reject(error);
    });
    // handle failure
    request.addEventListener("error", () => {
        const error = new ConnectionLostError(url);
        rpcBus.trigger("RPC:RESPONSE", { data, settings, error });
        reject(error);
    });
    // configure and send request
    request.open("POST", url);
    const headers = settings.headers || {};
    headers["Content-Type"] = "application/json";
    for (const [header, value] of Object.entries(headers)) {
        request.setRequestHeader(header, value);
    }
    request.send(JSON.stringify(data));
    /**
     * @param {boolean} rejectError Returns an error if true. Allows you to cancel
     *                  ignored rpc's in order to unblock the ui and not display an error.
     */
    /** @type {any} */ (promise).abort = function (rejectError = true) {
        if (request.abort) {
            request.abort();
        }
        const error = new ConnectionAbortedError("XmlHttpRequestError abort");
        rpcBus.trigger("RPC:RESPONSE", { data, settings, error });
        if (rejectError) {
            reject(error);
        }
    };
    return promise;
};
