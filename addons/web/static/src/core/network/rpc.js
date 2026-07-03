import { EventBus } from "@odoo/owl";
import { browser } from "../browser/browser";
import { omit } from "../utils/objects";
import { isDead, protect } from "../utils/use_async";

/**
 * @typedef {{
 *  code: number;
 *  message: string;
 *  data?: unknown;
 *  type?: string;
 * }} JsonRpcError
 */

export const rpcBus = new EventBus();

const RPC_SETTINGS = new Set(["cache", "silent", "xhr", "headers", "signal"]);
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
        return rpcCache.read(
            params?.method || url, // table
            JSON.stringify({ url, params }), // key
            () => rpc._rpc(url, params, omit(settings, "cache")),
            typeof settings.cache === "boolean" ? {} : settings.cache // cache can be boolean or an object with options (or an empty object of course)
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
            const { error: responseError, result: responseResult } = params;
            if (!params.error) {
                rpcBus.trigger("RPC:RESPONSE", { data, settings, result: params.result });
                return resolve(responseResult);
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
    // Cancel the in-flight request when an AbortSignal fires (e.g. the caller's
    // component scope is destroyed -- see rpc.toAsync). We stop listening once
    // the request settles, so a later abort of the (shared) signal does not
    // re-abort and re-trigger RPC:RESPONSE for an already-finished request.
    if (settings.signal) {
        const { signal } = settings;
        // abort(false): cancel the request but DON'T reject -- the caller's
        // continuation is dropped (left pending) by the scope guard, so a
        // rejection here would only surface as a spurious unhandled error.
        const onAbort = () => promise.abort(false);
        if (signal.aborted) {
            onAbort();
        } else {
            signal.addEventListener("abort", onAbort);
            const stopListening = () => signal.removeEventListener("abort", onAbort);
            promise.then(stopListening, stopListening);
        }
    }
    return promise;
};

/**
 * Scope-protocol (see `useAsync`): return a scope-bound rpc. Every call it
 * produces passes the scope's AbortSignal, so a destroyed component's in-flight
 * request is actually cancelled -- and the result is guarded, so the awaiting
 * continuation is dropped (AbortError) if the component dies right as the
 * response arrives.
 *
 *   rpc = useAsync(rpc);
 *   const res = await this.rpc("/some/route", {...});  // aborted on destroy
 *
 * @param {import("@odoo/owl").Scope} scope
 */
rpc.toAsync = function (scope) {
    return function (url, params, settings = {}) {
        if (isDead(scope)) {
            return new Promise(() => {}); // scope already gone: don't even send
        }
        const real = rpc(url, params, { ...settings, signal: scope.abortSignal });
        const guarded = protect(real, scope);
        guarded.abort = real.abort;
        return guarded;
    };
};
