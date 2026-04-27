/** @odoo-module **/

import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Component } from "@odoo/owl";

export class GroupMenu extends Component {
    static template = "mrp_mps.GroupMenu";
    static components = { CheckboxItem };
    static props = {
        items: Object,
    };

    get items() {
        return this.props.items;
    }

    _toggle_group(group) {
        const value = {};
        value[group] = !this.props.items[group];
        this.env.model._saveCompanySettings(value);
    }

}
