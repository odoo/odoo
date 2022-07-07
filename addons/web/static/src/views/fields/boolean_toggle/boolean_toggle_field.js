/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class BooleanToggleField extends Component {
    get isReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }
}

BooleanToggleField.template = "web.BooleanToggleField";
BooleanToggleField.components = { CheckBox };
BooleanToggleField.props = {
    ...standardFieldProps,
};

BooleanToggleField.displayName = _lt("Toggle");
BooleanToggleField.supportedTypes = ["boolean"];

BooleanToggleField.isEmpty = () => false;

registry.category("fields").add("boolean_toggle", BooleanToggleField);
