// @ts-check
/** @odoo-module native */

import { Component } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
export class StatusBarButtons extends Component {
    static template = "web.StatusBarButtons";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        slots: { type: Object, optional: 1 },
    };

    /** @returns {string[]} */
    get visibleSlotNames() {
        if (!this.props.slots) {
            return [];
        }
        const names = [];
        for (const [name, slot] of Object.entries(this.props.slots)) {
            if ("isVisible" in slot && !slot.isVisible) {
                continue;
            }
            if (slot.isSeparator && (!names.length || this.isSeparator(names.at(-1)))) {
                continue;
            }
            names.push(name);
        }
        if (names.length && this.isSeparator(names.at(-1))) {
            names.pop();
        }
        return names;
    }

    /** @returns {string[]} */
    get dropdownSlotNames() {
        const names = this.visibleSlotNames.slice(1);
        if (names.length && this.isSeparator(names[0])) {
            names.shift();
        }
        return names;
    }

    /**
     * @param {string} name
     * @returns {boolean}
     */
    isSeparator(name) {
        return Boolean(this.props.slots?.[name]?.isSeparator);
    }
}
