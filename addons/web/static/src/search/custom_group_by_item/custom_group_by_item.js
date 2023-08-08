/** @odoo-module **/

import { AccordionItem } from "@web/core/dropdown/accordion_item";

import { Component, useState } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class CustomGroupByItem extends Component {
    static template = "web.CustomGroupByItem";
    static components = { AccordionItem, DropdownItem };
    static props = {
        fields: Array,
        onAddCustomGroup: Function,
        closingMode: { type: String, optional: true },
    };
    static defaultProps = {
        closingMode: "none",
    };

    setup() {
        this.state = useState({});
        if (this.props.fields.length) {
            this.state.fieldName = this.props.fields[0].name;
        }
    }
}
