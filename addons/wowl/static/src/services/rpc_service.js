/** @odoo-module **/

import OdooError from "../errors/odoo_error";
import { serviceRegistry } from "../webclient/service_registry";

const { Component } = owl;

// -----------------------------------------------------------------------------
// Errors
// -----------------------------------------------------------------------------
export class RPCError extends OdooError {
  constructor() {
    super("RPC_ERROR");
    this.type = "server";
  }
}

export class ConnectionLostError extends OdooError {
  constructor() {
    super("CONNECTION_LOST_ERROR");
  }
}

// -----------------------------------------------------------------------------
// Main RPC method
// -----------------------------------------------------------------------------
function makeErrorFromResponse(reponse) {
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

let rpcId = 0;
function jsonrpc(env, url, params, rpcId, settings = {}) {
  const bus = env.bus;
  const XHR = odoo.browser.XMLHttpRequest;
  const data = {
    id: rpcId,
    jsonrpc: "2.0",
    method: "call",
    params: params,
  };
  return new Promise((resolve, reject) => {
    const request = new XHR();
    if (!settings.shadow) {
      bus.trigger("RPC:REQUEST", data.id);
    }
    // handle success
    request.addEventListener("load", () => {
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
}

// -----------------------------------------------------------------------------
// RPC service
// -----------------------------------------------------------------------------
export const rpcService = {
  name: "rpc",
  deploy(env) {
    return async function (route, params = {}, settings) {
      if (this instanceof Component) {
        if (this.__owl__.status === 5 /* DESTROYED */) {
          throw new Error("A destroyed component should never initiate a RPC");
        }
        const result = await jsonrpc(env, route, params, rpcId++, settings);
        if (this instanceof Component && this.__owl__.status === 5 /* DESTROYED */) {
          return new Promise(() => {});
        }
        return result;
      }
      return jsonrpc(env, route, params, rpcId++, settings);
    };
  },
};

serviceRegistry.add("rpc", rpcService);
