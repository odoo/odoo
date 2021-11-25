/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;
export class BadgeField extends Component {
    get decorationClasses() {
        let classes = "";
        for (const key in this.props.options.decorations) {
            if (this.props.options.decorations[key]) {
                classes += `bg-${key}-light `;
            }
        }
        return classes;
    }
}
BadgeField.template = "web.BadgeField";

registry.category("fields").add("badge", BadgeField);
