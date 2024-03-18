/** @odoo-module  */

import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

<<<<<<< HEAD
import { Component, onWillRender } from "@odoo/owl";
export class ButtonBox extends Component {
    setup() {
        const ui = useService("ui");
        onWillRender(() => {
            const maxVisibleButtons = [3, 4, 5, 7, 4, 5, 8][ui.size] || 8;
            const allVisibleButtons = Object.entries(this.props.slots)
                .filter(([_, slot]) => this.isSlotVisible(slot))
                .map(([slotName]) => slotName);
            if (allVisibleButtons.length <= maxVisibleButtons) {
                this.visibleButtons = allVisibleButtons;
                this.additionalButtons = [];
                this.isFull = allVisibleButtons.length === maxVisibleButtons;
            } else {
                // -1 for "More" dropdown
                this.visibleButtons = allVisibleButtons.slice(0, maxVisibleButtons - 1);
                this.additionalButtons = allVisibleButtons.slice(maxVisibleButtons - 1);
                this.isFull = true;
            }
        });
    }

    isSlotVisible(slot) {
        return !("isVisible" in slot) || slot.isVisible;
=======
import { Component } from "@odoo/owl";
export class ButtonBox extends Component {
    setup() {
        const ui = useService("ui");
        this.getMaxButtons = () => [2, 3, 4, 6, 3, 4, 7][ui.size] || 7;
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
>>>>>>> 66076f9a3d6c9e60ba2b45e8c02467ddac830181
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
