/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class LabelSelectionField extends Component {
    get className() {
        return this.props.classesObj[this.props.value] || "primary";
    }
    get string() {
        return this.props.value !== false
            ? this.props.options.find((o) => o[0] === this.props.value)[1]
            : "";
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        this.props.update(ev.target.value);
    }
}

LabelSelectionField.template = "web.LabelSelectionField";
LabelSelectionField.defaultProps = {
    classesObj: {},
};
LabelSelectionField.props = {
    ...standardFieldProps,
    classesObj: { type: Object, optional: true },
    options: Object,
};
LabelSelectionField.displayName = _lt("Label Selection");
LabelSelectionField.supportedTypes = ["selection"];
LabelSelectionField.extractProps = (fieldName, record, attrs) => {
    return {
        classesObj: attrs.options.classes,
        options: record.fields[fieldName].selection,
    };
};

registry.category("fields").add("label_selection", LabelSelectionField);
