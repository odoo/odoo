/** @odoo-module **/

import { Component } from "@odoo/owl";

export class CustomGroupByItem extends Component {
    get choices() {
        return this.props.fields.map((f) => ({ label: f.string, value: f.name }));
    }

    onSelected(ev) {
        if (ev.target.value) {
            this.props.onAddCustomGroup(ev.target.value);
            // reset the placeholder
            ev.target.value = "";
        }
    }
}

CustomGroupByItem.template = "web.CustomGroupByItem";
CustomGroupByItem.props = {
    fields: Array,
    onAddCustomGroup: Function,
};
