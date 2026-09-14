// @ts-check
/** @odoo-module native */

import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";

export class CogMenuItem extends Component {
    static template = "web.CogMenuItem";
    static components = { DropdownItem };
    static props = {
        description: String,
        icon: { type: String, optional: true },
        onSelected: { type: Function, optional: true },
        class: { type: String, optional: true },
        danger: { type: Boolean, optional: true },
        closingMode: { type: String, optional: true },
        attrs: { type: Object, optional: true },
        slots: { type: Object, optional: true },
    };

    /** @returns {string} */
    get itemClass() {
        return ["o_menu_item", this.props.class, this.props.danger ? "text-danger" : ""]
            .filter(Boolean)
            .join(" ");
    }
}
