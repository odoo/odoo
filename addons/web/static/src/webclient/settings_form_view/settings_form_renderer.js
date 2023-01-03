/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormLabelHighlightText } from "./highlight_text/form_label_highlight_text";
import { HighlightText } from "./highlight_text/highlight_text";
import { Setting } from "./settings/setting";
import { SettingHeader } from "./settings/setting_header";
import { SettingsBlock } from "./settings/settings_block";
import { SettingsApp } from "./settings/settings_app";
import { SettingsPage } from "./settings/settings_page";

import { useState } from "@odoo/owl";

const fieldRegistry = registry.category("fields");

const labels = Object.create(null);

export class SettingsFormRenderer extends FormRenderer {
    setup() {
        if (!labels[this.props.archInfo.arch]) {
            labels[this.props.archInfo.arch] = [];
        }
        super.setup();
        this.searchState = useState(this.env.searchState);
    }

    get shouldAutoFocus() {
        return false;
    }

    get compileParams() {
        return {
            ...super.compileParams,
            labels: labels[this.props.archInfo.arch],
            getFieldExpr: this.getFieldExpr,
            record: this.props.record,
        };
    }

    getFieldExpr(fieldName, fieldWidget) {
        const name = `base_settings.${fieldWidget}`;
        let fieldClass;
        if (fieldRegistry.contains(name)) {
            fieldClass = fieldRegistry.get(name);
        }
        if (fieldClass && fieldClass.extractStringExpr) {
            return fieldClass.extractStringExpr(fieldName, this.record);
        } else {
            return "";
        }
    }
}
SettingsFormRenderer.components = {
    ...FormRenderer.components,
    Setting,
    SettingHeader,
    SettingsBlock,
    SettingsPage,
    SettingsApp,
    HighlightText,
    FormLabel: FormLabelHighlightText,
};
SettingsFormRenderer.props = {
    ...FormRenderer.props,
    initialApp: String,
    slots: Object,
};
