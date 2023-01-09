/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formView } from "@web/views/form/form_view";
import { SettingsFormController } from "./settings_form_controller";
import { SettingsFormRenderer } from "./settings_form_renderer";
import { SettingsFormCompiler } from "./settings_form_compiler";
import BasicModel from "web.BasicModel";

const BaseSettingsModel = BasicModel.extend({
    save(recordID, options) {
        const savePoint = options && options.savePoint;
        return this._super.apply(this, arguments).then((result) => {
            if (!savePoint && this.localData[recordID].model === "res.config.settings") {
                // we remove here the res_id, because the record should still be
                // considered new.  We want the web client to always perform a
                // onchange to fetch the settings data.
                delete this.localData[recordID].res_id;
            }
            return result;
        });
    },
});

class SettingsRelationalModel extends formView.Model {}
SettingsRelationalModel.LegacyModel = BaseSettingsModel;

export const settingsFormView = {
    ...formView,
    display: {},
    buttonTemplate: "web.SettingsFormView.Buttons",
    Model: SettingsRelationalModel,
    ControlPanel: ControlPanel,
    Controller: SettingsFormController,
    Compiler: SettingsFormCompiler,
    Renderer: SettingsFormRenderer,
};

registry.category("views").add("base_settings", settingsFormView);
