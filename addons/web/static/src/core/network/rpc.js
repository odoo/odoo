import { EventBus, markup } from "@odoo/owl";
import { browser } from "../browser/browser";
import { omit } from "../utils/objects";

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
function validateRPCSettings(settings) {
    if (!Object.keys(settings).every((key) => RPC_SETTINGS.has(key))) {
        throw new Error(`The settings for rpc should be ${[...RPC_SETTINGS].join(" ")}`);
    }
    if ("cache" in settings && "xhr" in settings) {
        throw new Error("Can't use 'cache' and 'xhr' at the same time");
    }
}

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------
export class RPCError extends Error {
    constructor() {
        super(...arguments);
        this.name = "RPC_ERROR";
        this.type = "server";
        this.code = null;
        this.data = null;
        this.exceptionName = null;
        this.subType = null;
    }
}

export class ConnectionLostError extends Error {
    constructor(url, ...args) {
        const message = url
            ? `Connection to "${url}" couldn't be established or was interrupted`
            : "Connection couldn't be established or was interrupted";
        super(message, ...args);
        this.url = url;
    }
}

export class ConnectionAbortedError extends Error {}

export class RequestEntityTooLargeError extends Error {
    constructor() {
        super("The request you sent exceeded the maximum size limit configured on the server");
    }
}

/**
 * @param {JsonRpcError} response
 */
export function makeErrorFromResponse(response) {
    // Odoo returns error like this, in a error field instead of properly
    // using http error codes...
    const { code, data: errorData, message, type: subType } = response;
    const error = new RPCError();
    error.exceptionName = errorData?.name;
    error.subType = subType;
    error.data = errorData;
    error.message = message;
    error.code = code;
    return error;
}

// -----------------------------------------------------------------------------
// Markup
// -----------------------------------------------------------------------------

/**
 * Wraps the markup values of the result of a JSON-RPC response in markup, in
 * place.
 *
 * The server lists the paths to its `Markup` values in the `markup` member
 * of the response, each path being a list of object keys and array indices
 * from the root of the result.
 *
 * @param {{ result: unknown; markup?: (string | number)[][] }} response
 * @returns {unknown} the hydrated result
 */
function hydrateMarkup(response) {
    for (const path of response.markup || []) {
        if (!path.length) {
            response.result = markup(response.result);
            continue;
        }
        let parent = response.result;
        for (let i = 0; i < path.length - 1; i++) {
            parent = parent[path[i]];
        }
        const key = path.at(-1);
        parent[key] = markup(parent[key]);
    }
    return response.result;
}

// -----------------------------------------------------------------------------
// Cache RPC method
// -----------------------------------------------------------------------------

let rpcCache;

rpc.setCache = function (cache) {
    rpcCache = cache;
};

rpcBus.addEventListener("CLEAR-CACHES", (event) => {
    rpcCache?.invalidate(event.detail);
});

// -----------------------------------------------------------------------------
// Main RPC
// -----------------------------------------------------------------------------
let rpcId = 0;
export function rpc(url, params = {}, settings = {}) {
    return rpc._rpc(url, params, settings);
}
// such that it can be overriden in tests
rpc._rpc = function (url, params, settings) {
    validateRPCSettings(settings);
    if (settings.cache && rpcCache) {
        // cache can be boolean or an object with options (or an empty object of course)
        const cacheSettings = typeof settings.cache === "boolean" ? {} : { ...settings.cache };
        const { callback } = cacheSettings;
        // values are copied via a JSON roundtrip for each callback, as well as
        // the cache result (in both cache hit and cache miss cases), so need
        // hydration every time
        if (callback) {
            cacheSettings.callback = (response, hasChanged) =>
                callback(hydrateMarkup(response), hasChanged);
        }
        return rpcCache
            .read(
                params?.method || url, // table
                JSON.stringify({ url, params }), // key
                () => fetchResponse(url, params, settings),
                cacheSettings
            )
            .then(hydrateMarkup);
    }
    const promise = fetchResponse(url, params, settings);
    const result = promise.then((response) => response.result);
    result.abort = promise.abort;
    return result;
};

/**
 * Performs a JSON-RPC request, and resolves with its response, whose result is
 * hydrated (cf `hydrateMarkup`). Triggers the RPC:RESPONSE event on success.
 *
 * @param {string} url
 * @param {unknown} params
 * @param {Object} settings
 */
function fetchResponse(url, params, settings) {
    const data = {
        id: rpcId++,
        jsonrpc: "2.0",
        method: "call",
        params: params,
    };
    const promise = jsonrpc(url, data, settings);
    const response = promise.then((response) => {
        const result = hydrateMarkup(response);
        rpcBus.trigger("RPC:RESPONSE", { data, settings, result });
        return response;
    });
    response.abort = promise.abort;
    return response;
}

/**
 * Sends a JSON-RPC request, and resolves with the raw `result` and `markup` of
 * its response. Triggers the RPC:REQUEST event, and the RPC:RESPONSE event if
 * the request fails (it is up to the caller to trigger it on success).
 *
 * @param {string} url
 * @param {{ id: number; jsonrpc: "2.0"; method: "call"; params: unknown }} data
 * @param {Object} settings
 */
function jsonrpc(url, data, settings) {
    const XHR = browser.XMLHttpRequest;
    const request = settings.xhr || new XHR();
    let rejectFn;
    const promise = new Promise((resolve, reject) => {
        rejectFn = reject;
        rpcBus.trigger("RPC:REQUEST", { data, url, settings });
        // handle success
        request.addEventListener("load", () => {
            let specialError = null;
            switch (request.status) {
                // If Odoo is behind another server (eg.: nginx)
                case 502:
                    specialError = new ConnectionLostError(url);
                    break;
                //If the request content size exceeds the limit set by nginx, it will return an HTTP 413
                case 413:
                    specialError = new RequestEntityTooLargeError();
                    break;
            }
            if (specialError) {
                rpcBus.trigger("RPC:RESPONSE", { data, settings, error: specialError });
                reject(specialError);
                return;
            }
            let params;
            try {
                params = JSON.parse(request.response);
            } catch {
                // the response isn't json parsable, which probably means that the rpc request could
                // not be handled by the server, e.g. PoolError('The Connection Pool Is Full')
                const error = new ConnectionLostError(url);
                rpcBus.trigger("RPC:RESPONSE", { data, settings, error });
                return reject(error);
            }
            const { error: responseError } = params;
            if (!params.error) {
                return resolve({ result: params.result, markup: params.markup });
            }
            const error = makeErrorFromResponse(responseError);
            error.model = data.params.model;
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
    });
    /**
     * @param {Boolean} rejectError Returns an error if true. Allows you to cancel
     *                  ignored rpc's in order to unblock the ui and not display an error.
     */
    promise.abort = function (rejectError = true) {
        if (request.abort) {
            request.abort();
        }
        const error = new ConnectionAbortedError("XmlHttpRequestError abort");
        rpcBus.trigger("RPC:RESPONSE", { data, settings, error });
        if (rejectError) {
            rejectFn(error);
        }
    };
    return promise;
}
