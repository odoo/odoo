/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class Many2OneField extends Component {
    setup() {
        const data = this.props.record.data[this.props.name];
        this.data = data ? data[1] : "";
    }
}

Many2OneField.props = {
    ...standardFieldProps,
};
Many2OneField.template = "web.Many2OneField";

registry.category("fields").add("many2one", Many2OneField);
