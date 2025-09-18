// @ts-check

/** @module @web/views/form/status_bar_buttons/status_bar_buttons - Renders action buttons in the form status bar with overflow dropdown */

import { Component } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
/** Renders action buttons inside the form status bar, with overflow dropdown for excess items. */
export class StatusBarButtons extends Component {
    static template = "web.StatusBarButtons";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        slots: { type: Object, optional: 1 },
    };

    /** @returns {string[]} names of slots whose `isVisible` flag is true */
    get visibleSlotNames() {
        if (!this.props.slots) {
            return [];
        }
        return Object.entries(this.props.slots)
            .filter((entry) => entry[1].isVisible)
            .map((entry) => entry[0]);
    }
}
