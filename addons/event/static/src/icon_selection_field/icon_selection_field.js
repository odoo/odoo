/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const { Component } = owl;

export class IconSelectionField extends Component {
    get icon() {
        return this.props.icons[this.props.value];
    }
    get title() {
        return this.props.value.charAt(0).toUpperCase() + this.props.value.slice(1);
    }
}
IconSelectionField.template = "event.IconSelectionField";
IconSelectionField.props = {
    ...standardFieldProps,
    icons: Object,
};

IconSelectionField.displayName = _lt("Icon Selection");
IconSelectionField.supportedTypes = ["char", "text", "selection"];

IconSelectionField.extractProps = ({ attrs }) => ({
    icons: attrs.options,
});

registry.category("fields").add("event_icon_selection", IconSelectionField);
