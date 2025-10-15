import { EventBus } from "@odoo/owl";
import { browser } from "../browser/browser";

/**
 * @typedef {{
 *  code: number;
 *  message: string;
 *  data?: unknown;
 *  type?: string;
 * }} JsonRpcError
 */

export const rpcBus = new EventBus();

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
        super(`Connection to "${url}" couldn't be established or was interrupted`, ...args);
        this.url = url;
    }
}

export class ConnectionAbortedError extends Error {}

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
// Main RPC method
// -----------------------------------------------------------------------------
let rpcId = 0;
export function rpc(url, params = {}, settings = {}) {
    return rpc._rpc(url, params, settings);
}
// such that it can be overriden in tests
rpc._rpc = function (url, params, settings) {
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
            if (request.status === 502) {
                // If Odoo is behind another server (eg.: nginx)
                const error = new ConnectionLostError(url);
                rpcBus.trigger("RPC:RESPONSE", { data, settings, error });
                reject(error);
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
            error.id = data.id;
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
};
