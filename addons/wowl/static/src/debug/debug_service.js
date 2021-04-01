/** @odoo-module **/
import { serviceRegistry } from "../webclient/service_registry";
import { DebugManager } from "./debug_manager";

export function editModelDebug(env, title, model, id) {
  return env.services.action.doAction({
    res_model: model,
    res_id: id,
    name: title,
    type: "ir.actions.act_window",
    views: [[false, "form"]],
    view_mode: "form",
    target: "new",
    flags: { action_buttons: true, headless: true },
  });
}

export const debugService = {
  dependencies: ["orm"],
  async deploy(env) {
    let accessRightsProm;
    if (env.debug !== "") {
      odoo.systrayRegistry.add("wowl.debug_mode_menu", DebugManager, { sequence: 100 });
    }

    return {
      getAccessRights() {
        const { orm } = env.services;
        if (!accessRightsProm) {
          accessRightsProm = new Promise((resolve, reject) => {
            const accessRights = {
              canEditView: false,
              canSeeRecordRules: false,
              canSeeModelAccess: false,
            };
            const canEditView = orm
              .call("ir.ui.view", "check_access_rights", [], {
                operation: "write",
                raise_exception: false,
              })
              .then((result) => (accessRights.canEditView = result));
            const canSeeRecordRules = orm
              .call("ir.rule", "check_access_rights", [], {
                operation: "read",
                raise_exception: false,
              })
              .then((result) => (accessRights.canSeeRecordRules = result));
            const canSeeModelAccess = orm
              .call("ir.model.access", "check_access_rights", [], {
                operation: "read",
                raise_exception: false,
              })
              .then((result) => (accessRights.canSeeModelAccess = result));
            Promise.all([canEditView, canSeeRecordRules, canSeeModelAccess])
              .then(() => resolve(accessRights))
              .catch((error) => {
                accessRightsProm = undefined;
                reject(error);
              });
          });
        }
        return accessRightsProm;
      },
    };
  },
};

serviceRegistry.add("debug", debugService);
