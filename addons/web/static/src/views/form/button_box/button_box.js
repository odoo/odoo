/** @odoo-module  */

import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component } from "@odoo/owl";
export class ButtonBox extends Component {
    setup() {
        const ui = useService("ui");
        this.getMaxButtons = () => [3, 3, 3, 7, 3, 4, 7][ui.size] || 7;
    }

    getButtons() {
        const maxVisibleButtons = this.getMaxButtons();
        const visible = [];
        const additional = [];
        for (const [slotName, slot] of Object.entries(this.props.slots)) {
            if (!("isVisible" in slot) || slot.isVisible) {
                if (visible.length >= maxVisibleButtons) {
                    additional.push(slotName);
                } else {
                    visible.push(slotName);
                }
            }
        }
        return { visible, additional };
    }
}
ButtonBox.template = "web.Form.ButtonBox";
ButtonBox.components = { Dropdown, DropdownItem };
ButtonBox.props = {
    slots: Object,
    class: { type: String, optional: true },
};
ButtonBox.defaultProps = {
    class: "",
};
