/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class LabelSelectionField extends Component {
    get className() {
        return this.props.classesObj ? this.props.classesObj[this.props.value] : "primary";
    }
    get options() {
        return this.props.record.fields[this.props.name].selection;
    }
    get string() {
        return this.props.value !== false
            ? this.options.find((o) => o[0] === this.props.value)[1]
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
LabelSelectionField.props = {
    ...standardFieldProps,
    classesObj: { type: Object, optional: true },
};
LabelSelectionField.displayName = _lt("Label Selection");
LabelSelectionField.supportedTypes = ["selection"];
LabelSelectionField.convertAttrsToProps = (attrs) => {
    return {
        classesObj: attrs.options.classes,
    };
};

registry.category("fields").add("label_selection", LabelSelectionField);
