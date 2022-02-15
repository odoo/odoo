/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";
import { CheckBox } from "@web/core/checkbox/checkbox";

const { Component } = owl;

export class BooleanToggleField extends Component {
    /**
     * @param {Event} ev
     */
    onChange(newValue) {
        this.props.update(newValue);
    }
    /**
     * @param {MouseEvent} ev
     */
    onKeydown({ key }) {
        switch (key) {
            case "Enter":
                this.props.update(!this.props.value);
                break;
        }
    }
}

BooleanToggleField.template = "web.BooleanToggleField";
BooleanToggleField.props = {
    ...standardFieldProps,
};
BooleanToggleField.displayName = _lt("Toggle");
BooleanToggleField.supportedTypes = ["boolean"];
BooleanToggleField.isEmpty = () => false;
BooleanToggleField.components = { CheckBox };

registry.category("fields").add("boolean_toggle", BooleanToggleField);
