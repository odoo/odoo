/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;
export class BadgeField extends Component {
    get decorationClasses() {
        let classes = "";
        for (const key in this.props.decorations) {
            if (this.props.decorations[key]) {
                classes += `bg-${key}-light `;
            }
        }
        return classes;
    }
}
BadgeField.template = "web.BadgeField";

registry.category("fields").add("badge", BadgeField);
