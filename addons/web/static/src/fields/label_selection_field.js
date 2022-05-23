/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";
import { formatSelection } from "./formatters";

const { Component } = owl;

export class LabelSelectionField extends Component {
    get className() {
        return this.props.classesObj[this.props.value] || "primary";
    }
    get string() {
        return formatSelection(this.props.value, { selection: this.props.options });
    }
}

LabelSelectionField.template = "web.LabelSelectionField";
LabelSelectionField.props = {
    ...standardFieldProps,
    classesObj: { type: Object, optional: true },
    options: Object,
};
LabelSelectionField.defaultProps = {
    classesObj: {},
};

LabelSelectionField.displayName = _lt("Label Selection");
LabelSelectionField.supportedTypes = ["selection"];

LabelSelectionField.extractProps = (fieldName, record, attrs) => {
    return {
        classesObj: attrs.options.classes,
        options: Array.from(record.fields[fieldName].selection),
    };
};

registry.category("fields").add("label_selection", LabelSelectionField);
