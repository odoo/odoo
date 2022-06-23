/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { CheckBox } from "@web/core/checkbox/checkbox";

const { Component } = owl;

export class BooleanField extends Component {
    /**
     * @param {boolean} newValue
     */
    onChange(newValue) {
        this.props.update(newValue);
    }
}

BooleanField.template = "web.BooleanField";
BooleanField.components = { CheckBox };
BooleanField.props = {
    ...standardFieldProps,
    isReadonlyEnabled: { type: Boolean, optional: true },
};

BooleanField.displayName = _lt("Checkbox");
BooleanField.supportedTypes = ["boolean"];

BooleanField.isEmpty = () => false;
BooleanField.extractProps = (fieldName, record) => {
    return {
        // should we make a list specialization?
        readonly: !(record.isInEdition && !record.isReadonly(fieldName)),
        isReadonlyEnabled:
            record.activeFields[fieldName].viewType === "list" && !record.isReadonly(fieldName),
    };
};

registry.category("fields").add("boolean", BooleanField);
