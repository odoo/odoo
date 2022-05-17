/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;
const formatters = registry.category("formatters");

export class BadgeField extends Component {
    get formattedValue() {
        const formatter = formatters.get(this.props.type);
        return formatter(this.props.value, {
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
BadgeField.supportedTypes = ["selection", "many2one", "char"];

registry.category("fields").add("badge", BadgeField);
