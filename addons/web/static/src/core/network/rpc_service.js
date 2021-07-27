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

export class ConnectionLostError extends Error {}

export class ConnectionAbortedError extends Error {}

// -----------------------------------------------------------------------------
// Main RPC method
// -----------------------------------------------------------------------------
export function makeErrorFromResponse(reponse) {
    // Odoo returns error like this, in a error field instead of properly
    // using http error codes...
    const { code, data: errorData, message, type: subType } = reponse;
    const { context: data_context, name: data_name } = errorData || {};
    const { exception_class } = data_context || {};
    const exception_class_name = exception_class || data_name;
    const error = new RPCError();
    error.exceptionName = exception_class_name;
    error.subType = subType;
    error.data = errorData;
    error.message = message;
    error.code = code;
    return error;
}

function jsonrpc(env, rpcId, url, params, settings = {}) {
    const bus = env.bus;
    const XHR = browser.XMLHttpRequest;
    const data = {
        id: rpcId,
        jsonrpc: "2.0",
        method: "call",
        params: params,
    };
    const request = settings.xhr || new XHR();
    let rejectFn;
    const promise = new Promise((resolve, reject) => {
        rejectFn = reject;
        if (!settings.silent) {
            bus.trigger("RPC:REQUEST", data.id);
        }
        // handle success
        request.addEventListener("load", () => {
            if (request.status === 502) {
                // If Odoo is behind another server (eg.: nginx)
                bus.trigger("RPC:RESPONSE", data.id);
                reject(new ConnectionLostError());
                return;
            }
            const { error: responseError, result: responseResult } = JSON.parse(request.response);
            bus.trigger("RPC:RESPONSE", data.id);
            if (!responseError) {
                return resolve(responseResult);
            }
            const error = makeErrorFromResponse(responseError);
            reject(error);
        });
        // handle failure
        request.addEventListener("error", () => {
            bus.trigger("RPC:RESPONSE", data.id);
            reject(new ConnectionLostError());
        });
        // configure and send request
        request.open("POST", url);
        request.setRequestHeader("Content-Type", "application/json");
        request.send(JSON.stringify(data));
    });
    promise.abort = function () {
        if (request.abort) {
            request.abort();
        }
        rejectFn(new ConnectionAbortedError("XmlHttpRequestError abort"));
    };
    return promise;
}

// -----------------------------------------------------------------------------
// RPC service
// -----------------------------------------------------------------------------
String.prototype.hashCode = function() {
    var hash = 0, i, chr;
    if (this.length === 0) return hash;
    for (i = 0; i < this.length; i++) {
        chr   = this.charCodeAt(i);
        hash  = ((hash << 5) - hash) + chr;
        hash |= 0; // Convert to 32bit integer
    }
    return hash;
};
export const rpcService = {
    async: true,
    start(env) {
        let rpcId = 0;
        return function rpc(route, params = {}, settings) {
            if (route == "/web/dataset/search_read" && window.localStorage['fast-menu-opening-proof-of-concept']) {
                const localStorage = window.localStorage;
                const key = 'fast-menu-' + (route + JSON.stringify(params) + JSON.stringify(settings)).hashCode();
                if (localStorage.getItem(key)){
                    return new Promise((resolve, reject) => {
                        resolve(JSON.parse(localStorage.getItem(key)));
                    });
                } else {
                    return jsonrpc(env, rpcId++, route, params, settings).then(result => {
                        localStorage.setItem(key, JSON.stringify(result));
                        return result;
                    });
                }
            }
            return jsonrpc(env, rpcId++, route, params, settings);
        };
    },
};

registry.category("services").add("rpc", rpcService);
