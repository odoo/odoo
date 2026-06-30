/** @odoo-module **/

import { browser } from "../browser/browser";
import { registry } from "../registry";

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

// -----------------------------------------------------------------------------
// Main RPC method
// -----------------------------------------------------------------------------
export function makeErrorFromResponse(reponse) {
    // Odoo returns error like this, in a error field instead of properly
    // using http error codes...
    const { code, data: errorData, message, type: subType } = reponse;
    const error = new RPCError();
    error.exceptionName = errorData.name;
    error.subType = subType;
    error.data = errorData;
    error.message = message;
    error.code = code;
    return error;
}

let rpcId = 0;
export function jsonrpc(url, params = {}, settings = {}) {
    const bus = settings.bus;
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
        bus?.trigger("RPC:REQUEST", { data, url, settings });
        // handle success
        request.addEventListener("load", () => {
            if (request.status === 502) {
                // If Odoo is behind another server (eg.: nginx)
                const error = new ConnectionLostError(url);
                bus?.trigger("RPC:RESPONSE", { data, settings, error });
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
                bus?.trigger("RPC:RESPONSE", { data, settings, error });
                return reject(error);
            }
            const { error: responseError, result: responseResult } = params;
            if (!params.error) {
                bus?.trigger("RPC:RESPONSE", { data, settings, result: params.result });
                return resolve(responseResult);
            }
            const error = makeErrorFromResponse(responseError);
            bus?.trigger("RPC:RESPONSE", { data, settings, error });
            reject(error);
        });
        // handle failure
        request.addEventListener("error", () => {
            const error = new ConnectionLostError(url);
            bus?.trigger("RPC:RESPONSE", { data, settings, error });
            reject(error);
        });
        // configure and send request
        request.open("POST", url);
        const headers = settings.headers || {};
        headers["Content-Type"] = "application/json";
        for (let [header, value] of Object.entries(headers)) {
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
        bus?.trigger("RPC:RESPONSE", { data, settings, error });
        if (rejectError) {
            rejectFn(error);
        }
    };
    return promise;
}

// -----------------------------------------------------------------------------
// RPC service
// -----------------------------------------------------------------------------
export const rpcService = {
    async: true,
    start(env) {
        /**
         * @param {string} route
         * @param {Object} params
         * @param {Object} [settings]
         * @param {boolean} settings.silent
         * @param {XMLHttpRequest} settings.xhr
         */
        return function rpc(route, params = {}, settings = {}) {
            return jsonrpc(route, params, { bus: env.bus, ...settings });
        };
    },
};

registry.category("services").add("rpc", rpcService);
