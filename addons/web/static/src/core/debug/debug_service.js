/** @odoo-module **/

import { registry } from "../registry";
import { DebugManager } from "./debug_menu";

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
    start(env, { orm }) {
        let accessRightsProm;
        if (env.debug !== "") {
            registry
                .category("systray")
                .add("web.debug_mode_menu", DebugManager, { sequence: 100 });
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

registry.category("services").add("debug", debugService);
