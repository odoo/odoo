/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

export class BooleanIconField extends Component {
    get label() {
        return this.props.record.activeFields[this.props.name].string;
    }
}
BooleanIconField.defaultProps = {
    icon: "fa-check-square-o",
};
BooleanIconField.extractProps = ({ attrs }) => {
    return {
        icon: attrs.options.icon,
    };
};
BooleanIconField.template = "web.BooleanIconField";
BooleanIconField.props = {
    ...standardFieldProps,
    icon: { type: String, optional: true },
};
BooleanIconField.displayName = _lt("Boolean Icon");
BooleanIconField.supportedTypes = ["boolean"];

registry.category("fields").add("boolean_icon", BooleanIconField);
