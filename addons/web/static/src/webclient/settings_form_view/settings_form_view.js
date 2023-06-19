/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formView } from "@web/views/form/form_view";
import { SettingsFormController } from "./settings_form_controller";
import { SettingsFormRenderer } from "./settings_form_renderer";
import { SettingsFormCompiler } from "./settings_form_compiler";
import BasicModel from "web.BasicModel";
import { SettingsArchParser } from "./settings_form_arch_parser";

const BaseSettingsModel = BasicModel.extend({
    isNew(id) {
        return this.localData[id].model === "res.config.settings"
            ? true
            : this._super.apply(this, arguments);
    },
    _applyChange: function (recordID, changes, options) {
        // Check if the changes isHeaderField.
        const record = this.localData[recordID];
        let isHeaderField = false;
        for (const fieldName of Object.keys(changes)) {
            const fieldInfo = record.fieldsInfo[options.viewType][fieldName];
            isHeaderField = fieldInfo.options && fieldInfo.options.isHeaderField;
        }
        if (isHeaderField) {
            options.doNotSetDirty = true;
        }
        return this._super.apply(this, arguments);
    },
});

class SettingsRelationalModel extends formView.Model {}
SettingsRelationalModel.LegacyModel = BaseSettingsModel;

export const settingsFormView = {
    ...formView,
    display: {},
    buttonTemplate: "web.SettingsFormView.Buttons",
    ArchParser: SettingsArchParser,
    Model: SettingsRelationalModel,
    ControlPanel: ControlPanel,
    Controller: SettingsFormController,
    Compiler: SettingsFormCompiler,
    Renderer: SettingsFormRenderer,
};

registry.category("views").add("base_settings", settingsFormView);
