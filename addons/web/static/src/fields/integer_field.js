/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
export class IntegerField extends Component {
    onChange(ev) {
        let isValid = true;
        let value = ev.target.value;
        try {
            value = this.props.parse(value);
        } catch (e) {
            isValid = false;
            this.props.record.setInvalidField(this.props.name);
        }
        if (isValid) {
            this.props.update(value);
        }
    }

    get formattedInputValue() {
        if (this.props.inputType === "number") return this.props.value;
        return this.props.format(this.props.value, {
            field: this.props.record.fields[this.props.name],
        });
    }
}

IntegerField.template = "web.IntegerField";
IntegerField.props = {
    ...standardFieldProps,
    inputType: { type: String, optional: true },
};
IntegerField.defaultProps = {
    inputType: "text",
};
IntegerField.isEmpty = () => false;
IntegerField.convertAttrsToProps = (attrs) => {
    return {
        inputType: attrs.options.type,
    };
};

registry.category("fields").add("integer", IntegerField);
