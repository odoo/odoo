/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;
export class BadgeField extends Component {
    get classFromDecoration() {
        for (const decorationName in this.props.decorations) {
            console.log(decorationName);
            if (this.props.decorations[decorationName]) {
                return `bg-${decorationName}-light`;
            }
        }
        return "";
    }
}
BadgeField.template = "web.BadgeField";

registry.category("fields").add("badge", BadgeField);
