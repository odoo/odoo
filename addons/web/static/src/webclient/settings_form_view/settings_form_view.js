/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formView } from "@web/views/form/form_view";
import { SettingsFormController } from "./settings_form_controller";
import { SettingsFormRenderer } from "./settings_form_renderer";
import { SettingsFormCompiler } from "./settings_form_compiler";
import BasicModel from "web.BasicModel";

const BaseSettingsModel = BasicModel.extend({
    isNew(id) {
        return this.localData[id].model === "res.config.settings"
            ? true
            : this._super.apply(this, arguments);
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
