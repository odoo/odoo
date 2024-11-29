import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component } from "@odoo/owl";

export class StatusBarButtons extends Component {
    static template = "web.StatusBarButtons";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        slots: { type: Object, optional: 1 },
    };

    get visibleSlotNames() {
        if (!this.props.slots) {
            return [];
        }
        return Object.entries(this.props.slots)
            .filter((entry) => entry[1].isVisible)
            .map((entry) => entry[0]);
    }
}
