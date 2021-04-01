/** @odoo-module **/

import { errorDialogRegistry } from "./error_dialog_registry";
import {
  ClientErrorDialog,
  ErrorDialog,
  NetworkErrorDialog,
  RPCErrorDialog,
} from "./error_dialogs";
import { errorHandlerRegistry } from "./error_handler_registry";
import { browser } from "../core/browser";

/**
 * @typedef {import("../env").OdooEnv} OdooEnv
 * @typedef {(error: any) => boolean | void} ErrorHandler
 */

// -----------------------------------------------------------------------------
// CORS errors
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @returns {ErrorHandler}
 */
function corsErrorHandler(env) {
  return (error) => {
    if (error.name === "UNKNOWN_CORS_ERROR") {
      env.services.dialog.open(NetworkErrorDialog, {
        traceback: error.traceback || error.stack,
        message: error.message,
        name: error.name,
      });
      return true;
    }
  };
}
errorHandlerRegistry.add("corsErrorHandler", corsErrorHandler, { sequence: 95 });

// -----------------------------------------------------------------------------
// Client errors
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @returns {ErrorHandler}
 */
function clientErrorHandler(env) {
  return (error) => {
    if (error.name === "UNCAUGHT_CLIENT_ERROR") {
      env.services.dialog.open(ClientErrorDialog, {
        traceback: error.traceback || error.stack,
        message: error.message,
        name: error.name,
      });
      return true;
    }
  };
}
errorHandlerRegistry.add("clientErrorHandler", clientErrorHandler, { sequence: 96 });

// -----------------------------------------------------------------------------
// Empty rejection errors
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @returns {ErrorHandler}
 */
function emptyRejectionErrorHandler(env) {
  return (error) => {
    if (error.name === "UNCAUGHT_EMPTY_REJECTION_ERROR") {
      env.services.dialog.open(ClientErrorDialog, {
        message: error.message,
        name: error.name,
      });
      return true;
    }
  };
}
errorHandlerRegistry.add("emptyRejectionErrorHandler", emptyRejectionErrorHandler, {
  sequence: 97,
});

// -----------------------------------------------------------------------------
// RPC errors
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @returns {ErrorHandler}
 */
function rpcErrorHandler(env) {
  return (error) => {
    if (error.name === "RPC_ERROR") {
      // When an error comes from the server, it can have an exeption name.
      // (or any string truly). It is used as key in the error dialog from
      // server registry to know which dialog component to use.
      // It's how a backend dev can easily map its error to another component.
      // Note that for a client side exception, we don't use this registry
      // as we can directly assign a value to `component`.
      // error is here a RPCError
      const exceptionName = error.exceptionName;
      let ErrorComponent = error.Component;
      if (!ErrorComponent && exceptionName && errorDialogRegistry.contains(exceptionName)) {
        ErrorComponent = errorDialogRegistry.get(exceptionName);
      }
      env.services.dialog.open(ErrorComponent || RPCErrorDialog, {
        traceback: error.traceback || error.stack,
        message: error.message,
        name: error.name,
        exceptionName: error.exceptionName,
        data: error.data,
        subType: error.subType,
        code: error.code,
        type: error.type,
      });
      return true;
    }
  };
}
errorHandlerRegistry.add("rpcErrorHandler", rpcErrorHandler, { sequence: 98 });

// -----------------------------------------------------------------------------
// Lost connection errors
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @returns {ErrorHandler}
 */
function lostConnectionHandler(env) {
  let connectionLostNotifId;
  return (error) => {
    if (error.name === "CONNECTION_LOST_ERROR") {
      if (connectionLostNotifId) {
        // notification already displayed (can occur if there were several
        // concurrent rpcs when the connection was lost)
        return true;
      }
      connectionLostNotifId = env.services.notification.create(
        env._t("Connection lost. Trying to reconnect..."),
        { sticky: true }
      );
      let delay = 2000;
      browser.setTimeout(function checkConnection() {
        env.services
          .rpc("/web/webclient/version_info", {})
          .then(function () {
            env.services.notification.close(connectionLostNotifId);
            connectionLostNotifId = null;
            env.services.notification.create(env._t("Connection restored. You are back online."), {
              type: "info",
            });
          })
          .catch((e) => {
            // exponential backoff, with some jitter
            delay = delay * 1.5 + 500 * Math.random();
            browser.setTimeout(checkConnection, delay);
          });
      }, delay);
      return true;
    }
  };
}
errorHandlerRegistry.add("lostConnectionHandler", lostConnectionHandler, { sequence: 99 });

// -----------------------------------------------------------------------------
// Default handler
// -----------------------------------------------------------------------------

/**
 * @param {OdooEnv} env
 * @returns {ErrorHandler}
 */
function defaultHandler(env) {
  return (error) => {
    const DialogComponent = error.Component || ErrorDialog;
    env.services.dialog.open(DialogComponent, {
      traceback: error.traceback || error.stack,
      message: error.message,
      name: error.name,
    });
    return true;
  };
}
errorHandlerRegistry.add("defaultHandler", defaultHandler, { sequence: 100 });
