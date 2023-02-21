/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { formatSelection } from "../formatters";

import { Component } from "@odoo/owl";

export class LabelSelectionField extends Component {
    static template = "web.LabelSelectionField";
    static props = {
        ...standardFieldProps,
        classesObj: { type: Object, optional: true },
    };
    static defaultProps = {
        classesObj: {},
    };

    get className() {
        return this.props.classesObj[this.props.value] || "primary";
    }
    get string() {
        return formatSelection(this.props.value, {
            selection: Array.from(this.props.record.fields[this.props.name].selection),
        });
    }
}

export const labelSelectionField = {
    component: LabelSelectionField,
    displayName: _lt("Label Selection"),
    supportedTypes: ["selection"],
    extractProps: ({ options }) => ({
        classesObj: options.classes,
    }),
};

registry.category("fields").add("label_selection", labelSelectionField);
