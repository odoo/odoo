/** @odoo-module **/

import { registry } from "@web/core/registry";
import { escapeRegExp } from "@web/core/utils/strings";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormLabelHighlightText } from "./highlight_text/form_label_highlight_text";
import { HighlightText } from "./highlight_text/highlight_text";
import { SettingsApp } from "./settings/settings_app";
import { SettingsPage } from "./settings/settings_page";
import { SettingsFormCompiler } from "./settings_form_compiler";

const { useState } = owl;

const fieldRegistry = registry.category("fields");

export class SettingsFormRender extends FormRenderer {
    setup() {
        this.labels = [];
        this.compileParams = {
            labels: this.labels,
            getFieldExpr: this.getFieldExpr,
            record: this.record,
        };
        super.setup();
        this.searchValue = useState(this.env.searchValue);
    }
    search(kind, value) {
        const labels = this.labels
            .filter((x) => x[kind] === value)
            .map((x) => [x.label, x.groupName]);
        return labels.join().match(new RegExp(`(${escapeRegExp(this.searchValue.value)})`, "ig"));
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
SettingsFormRender.components = {
    ...FormRenderer.components,
    SettingsPage,
    SettingsApp,
    HighlightText,
    FormLabel: FormLabelHighlightText,
};
SettingsFormRender.compiler = SettingsFormCompiler;
