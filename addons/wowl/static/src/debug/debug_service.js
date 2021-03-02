/** @odoo-module **/
import { serviceRegistry } from "../services/service_registry";
import { debugManager } from "./debug_manager";

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
  name: "debug",
  dependencies: ["model"],
  async deploy(env) {
    let accessRightsProm;
    if (env.debug !== "") {
      odoo.systrayRegistry.add("wowl.debug_mode_menu", debugManager);
    }
    
    return {
      getAccessRights() {
        if (!accessRightsProm) {
          accessRightsProm = new Promise((resolve, reject) => {
            const accessRights = {
              canEditView: false,
              canSeeRecordRules: false,
              canSeeModelAccess: false,
            };
            const canEditView = env.services
              .model("ir.ui.view")
              .call("check_access_rights", [], { operation: "write", raise_exception: false })
              .then((result) => (accessRights.canEditView = result));
            const canSeeRecordRules = env.services
              .model("ir.rule")
              .call("check_access_rights", [], { operation: "read", raise_exception: false })
              .then((result) => (accessRights.canSeeRecordRules = result));
            const canSeeModelAccess = env.services
              .model("ir.model.access")
              .call("check_access_rights", [], { operation: "read", raise_exception: false })
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