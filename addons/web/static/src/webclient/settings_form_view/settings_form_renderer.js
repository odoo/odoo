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
            record: this.props.record,
        };
        super.setup();
        this.searchState = useState(this.env.searchState);
    }
    search(kind, value) {
        const regexp = new RegExp(escapeRegExp(this.searchState.value), "i");
        for (const x of labels[this.props.archInfo.arch]) {
            if (x[kind] === value) {
                if (regexp.test([x.label, x.groupTitle, x.groupTip].join())) {
                    return true;
                }
            }
        }
        return false;
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
