/** @odoo-module **/

import { registry } from "@web/core/registry";
import { escapeRegExp } from "@web/core/utils/strings";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormLabelHighlightText } from "./highlight_text/form_label_highlight_text";
import { HighlightText } from "./highlight_text/highlight_text";
import { SettingsApp } from "./settings/settings_app";
import { SettingsPage } from "./settings/settings_page";

const { useState } = owl;

const fieldRegistry = registry.category("fields");

const labels = Object.create(null);

export class SettingsFormRenderer extends FormRenderer {
    setup() {
        if (!labels[this.props.archInfo.arch]) {
            labels[this.props.archInfo.arch] = [];
        }
        this.compileParams = {
            labels: labels[this.props.archInfo.arch],
            getFieldExpr: this.getFieldExpr,
            record: this.record,
        };
        super.setup();
        this.searchValue = useState(this.env.searchValue);
    }
    search(kind, value) {
        const labelsTmp = labels[this.props.archInfo.arch]
            .filter((x) => x[kind] === value)
            .map((x) => [x.label, x.groupName]);
        return labelsTmp
            .join()
            .match(new RegExp(`(${escapeRegExp(this.searchValue.value)})`, "ig"));
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
    SettingsPage,
    SettingsApp,
    HighlightText,
    FormLabel: FormLabelHighlightText,
};
