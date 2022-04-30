/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { SettingsFormController } from "./settings_form_controller";
import { SettingsFormRenderer } from "./settings_form_renderer";
import { SettingsFormCompiler } from "./settings_form_compiler";

const settingsFormView = {
    ...formView,
    display: {},
    buttonTemplate: "web.SettingsFormView.Buttons",
    Controller: SettingsFormController,
    Compiler: SettingsFormCompiler,
    Renderer: SettingsFormRenderer,
};

registry.category("views").add("base_settings", settingsFormView);
