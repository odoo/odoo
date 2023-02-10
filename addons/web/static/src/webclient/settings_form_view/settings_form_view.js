/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formView } from "@web/views/form/form_view";
import { SettingsFormController } from "./settings_form_controller";
import { SettingsFormRenderer } from "./settings_form_renderer";
import { SettingsFormCompiler } from "./settings_form_compiler";

class SettingModel extends formView.Model {
    async load(params = {}) {
        delete params.resId;
        return super.load(params);
    }
}

export const settingsFormView = {
    ...formView,
    display: {},
    buttonTemplate: "web.SettingsFormView.Buttons",
    Model: SettingModel,
    ControlPanel: ControlPanel,
    Controller: SettingsFormController,
    Compiler: SettingsFormCompiler,
    Renderer: SettingsFormRenderer,
};

registry.category("views").add("base_settings", settingsFormView);
