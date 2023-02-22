/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const { Component } = owl;

export class IconSelectionField extends Component {
    get icon() {
        return this.props.icons[this.props.record.data[this.props.name]];
    }
    get title() {
        return (
            this.props.record.data[this.props.name].charAt(0).toUpperCase() +
            this.props.record.data[this.props.name].slice(1)
        );
    }
}
IconSelectionField.template = "event.IconSelectionField";
IconSelectionField.props = {
    ...standardFieldProps,
    icons: Object,
};

export const iconSelectionField = {
    component: IconSelectionField,
    displayName: _lt("Icon Selection"),
    supportedTypes: ["char", "text", "selection"],
    extractProps: ({ options }) => ({
        icons: options,
    }),
};

registry.category("fields").add("event_icon_selection", iconSelectionField);
