/** @odoo-module **/

import { browser } from "../core/browser";
import AbstractStorageService from "web.AbstractStorageService";
import { RPCError } from "../services/rpc_service";

export function mapDoActionOptionAPI(legacyOptions) {
  legacyOptions = Object.assign(legacyOptions || {});
  // use camelCase instead of snake_case for some keys
  Object.assign(legacyOptions, {
    additionalContext: legacyOptions.additional_context,
    clearBreadcrumbs: legacyOptions.clear_breadcrumbs,
    viewType: legacyOptions.view_type,
    resId: legacyOptions.res_id,
    onClose: legacyOptions.on_close,
  });
  delete legacyOptions.additional_context;
  delete legacyOptions.clear_breadcrumbs;
  delete legacyOptions.view_type;
  delete legacyOptions.res_id;
  delete legacyOptions.on_close;
  return legacyOptions;
}

export function makeLegacyActionManagerService(legacyEnv) {
  // add a service to redirect 'do-action' events triggered on the bus in the
  // legacy env to the action-manager service in the wowl env
  return {
    name: "legacy_action_manager",
    dependencies: ["action"],
    start(env) {
      legacyEnv.bus.on("do-action", null, (payload) => {
        const legacyOptions = mapDoActionOptionAPI(payload.options);
        env.services.action.doAction(payload.action, legacyOptions);
      });
    },
  };
}

export function makeLegacyRpcService(legacyEnv) {
  return {
    name: "legacy_rpc",
    start(env) {
      legacyEnv.bus.on("rpc_request", null, (rpcId) => {
        env.bus.trigger("RPC:REQUEST", rpcId);
      });
      legacyEnv.bus.on("rpc_response", null, (rpcId) => {
        env.bus.trigger("RPC:RESPONSE", rpcId);
      });
      legacyEnv.bus.on("rpc_response_failed", null, (rpcId) => {
        env.bus.trigger("RPC:RESPONSE", rpcId);
      });
    },
  };
}

/**
 * Returns a service that maps legacy dialogs
 * to new environment services behavior.
 *
 * @param {object} legacyEnv
 * @returns a wowl deployable service
 */
export function makeLegacyDialogMappingService(legacyEnv) {
  return {
    dependencies: ["ui", "hotkey"],
    start(env) {
      const { ui, hotkey } = env.services;

      function getModalEl(dialog) {
        return dialog.modalRef
          ? dialog.modalRef.el
          : dialog.$modal[0];
      }

      function getCloseCallback(dialog) {
        return dialog.modalRef
          ? () => dialog._close()
          : () => dialog.$modal.modal("hide");
      }

      const tokensMap = new Map();

      function onOpenDialog(dialog) {
        ui.activateElement(getModalEl(dialog));
        const token = hotkey.registerHotkey(
          "escape",
          getCloseCallback(dialog),
          { altIsOptional: true }
        );
        tokensMap.set(token, dialog);
      }

      function onCloseDialog(dialog) {
        for (const [token, d] of tokensMap) {
          if (d === dialog) {
            ui.deactivateElement(getModalEl(dialog));
            hotkey.unregisterHotkey(token);
            tokensMap.delete(token);
            break;
          }
        }
      }

      legacyEnv.bus.on("legacy_dialog_opened", null, onOpenDialog);
      legacyEnv.bus.on("legacy_dialog_destroyed", null, onCloseDialog);

      legacyEnv.bus.on("owl_dialog_mounted", null, onOpenDialog);
      legacyEnv.bus.on("owl_dialog_willunmount", null, onCloseDialog);
    },
  };
}

export function makeLegacySessionService(legacyEnv, session) {
  return {
    name: "legacy_session",
    dependencies: ["user"],
    start(env) {
      // userContext, Object.create is incompatible with legacy new Context
      function mapContext() {
        return Object.assign({}, env.services.user.context);
      }
      Object.defineProperty(legacyEnv.session, "userContext", {
        get: () => mapContext(),
      });
      Object.defineProperty(session, "user_context", {
        get: () => mapContext(),
      });
    },
  };
}

export function mapLegacyEnvToWowlEnv(legacyEnv, wowlEnv) {
  // rpc
  legacyEnv.session.rpc = (...args) => {
    let rejection;
    let error;
    let event;
    const prom = new Promise((resolve, reject) => {
      rejection = () => reject();
      const [route, params, settings] = args;
      wowlEnv.services.rpc(route, params, settings).then(resolve).catch((reason) => {
        error = reason;
        if (isPrototypeOf.call(RPCError.prototype, reason)) {
          event = $.Event();
          reject({ message: reason, event });
        }
        reject(reason);
      });
    });
    prom.abort = rejection;
    prom.catch(() => {
      setTimeout(function () {
        // we want to execute this handler after all others (hence
        // setTimeout) to let the other handlers prevent the event
        if (!event || !event.isDefaultPrevented()) {
          return Promise.reject(error);
        }
      }, 0);
    });
    return prom;
  };
  // Storages
  function mapStorage(storage) {
    const StorageService = AbstractStorageService.extend({ storage });
    return new StorageService();
  }

  legacyEnv.services.local_storage = mapStorage(browser.localStorage);
  legacyEnv.services.session_storage = mapStorage(browser.sessionStorage);
  // map WebClientReady
  wowlEnv.bus.on("WEB_CLIENT_READY", null, () => {
    legacyEnv.bus.trigger("web_client_ready");
  });
}

export function breadcrumbsToLegacy(breadcrumbs) {
  if (!breadcrumbs) {
    return;
  }
  return breadcrumbs.slice().map((bc) => {
    return { title: bc.name, controllerID: bc.jsId };
  });
}
