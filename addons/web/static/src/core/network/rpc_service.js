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
    const error = new RPCError();
    error.exceptionName = errorData.name;
    error.subType = subType;
    error.data = errorData;
    error.message = message;
    error.code = code;
    return error;
}

export function jsonrpc(env, rpcId, url, params, settings = {}) {
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
                if (!settings.silent) {
                    bus.trigger("RPC:RESPONSE", data.id);
                }
                reject(new ConnectionLostError());
                return;
            }
            const { error: responseError, result: responseResult } = JSON.parse(request.response);
            if (!settings.silent) {
                bus.trigger("RPC:RESPONSE", data.id);
            }
            if (!responseError) {
                return resolve(responseResult);
            }
            const error = makeErrorFromResponse(responseError);
            reject(error);
        });
        // handle failure
        request.addEventListener("error", () => {
            if (!settings.silent) {
                bus.trigger("RPC:RESPONSE", data.id);
            }
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
export const rpcService = {
    async: true,
    start(env) {
        let rpcId = 0;
        return function rpc(route, params = {}, settings) {
            return jsonrpc(env, rpcId++, route, params, settings);
        };
    },
};

registry.category("services").add("rpc", rpcService);
