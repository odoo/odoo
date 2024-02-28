/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { CheckBox } from "@web/core/checkbox/checkbox";

import { Component } from "@odoo/owl";

export class BooleanField extends Component {
    get isReadonly() {
        return !(this.props.record.isInEdition && !this.props.record.isReadonly(this.props.name));
    }

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
};

BooleanField.displayName = _lt("Checkbox");
BooleanField.supportedTypes = ["boolean"];

BooleanField.isEmpty = () => false;

registry.category("fields").add("boolean", BooleanField);
