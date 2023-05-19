/** @odoo-module **/

import { AccordionItem } from "@web/core/dropdown/accordion_item";

import { Component, useState } from "@odoo/owl";

export class CustomGroupByItem extends Component {
    setup() {
        this.state = useState({});
        if (this.props.fields.length) {
            this.state.fieldName = this.props.fields[0].name;
        }
    }
}

CustomGroupByItem.template = "web.CustomGroupByItem";
CustomGroupByItem.components = { AccordionItem };
CustomGroupByItem.props = {
    fields: Array,
    onAddCustomGroup: Function,
};
