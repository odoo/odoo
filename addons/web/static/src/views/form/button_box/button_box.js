import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component, onWillRender } from "@odoo/owl";
export class ButtonBox extends Component {
    static template = "web.Form.ButtonBox";
    static components = { Dropdown, DropdownItem };
    static props = {
        slots: Object,
        class: { type: String, optional: true },
    };
    static defaultProps = {
        class: "",
    };

    setup() {
        const ui = useService("ui");
        onWillRender(() => {
            this.updateButtonVisibility([3, 4, 5, 7, 4, 5, 8][ui.size] || 8);
        });
    }

    updateButtonVisibility(maxVisibleButtons) {
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
    }

    isSlotVisible(slot) {
        return !("isVisible" in slot) || slot.isVisible;
    }
}
