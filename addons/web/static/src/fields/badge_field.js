/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;
export class BadgeField extends Component {
    get formattedValue() {
        return this.props.formatValue(this.props.value, {
            selection: this.props.record.fields[this.props.name].selection,
        });
    }

    get classFromDecoration() {
        for (const decorationName in this.props.decorations) {
            if (this.props.decorations[decorationName]) {
                return `bg-${decorationName}-light`;
            }
        }
        return "";
    }
}
BadgeField.template = "web.BadgeField";

registry.category("fields").add("badge", BadgeField);
