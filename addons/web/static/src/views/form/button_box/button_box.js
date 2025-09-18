// @ts-check

/** @module @web/views/form/button_box/button_box - Responsive stat-button container with overflow dropdown for form views */

import { Component, onWillRender } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
/** Responsive container for stat buttons at the top of form views, with overflow dropdown. */
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
            const maxVisibleButtons = [0, 0, 7, 4, 5, 8][ui.size] ?? 8;
            const allVisibleButtons = Object.entries(this.props.slots)
                .filter(([_, slot]) => this.isSlotVisible(slot))
                .map(([slotName]) => slotName);
            if (allVisibleButtons.length <= maxVisibleButtons) {
                this.visibleButtons = allVisibleButtons;
                this.additionalButtons = [];
                this.isFull = allVisibleButtons.length === maxVisibleButtons;
            } else {
                // -1 for "More" dropdown
                const splitIndex = Math.max(maxVisibleButtons - 1, 0);
                this.visibleButtons = allVisibleButtons.slice(0, splitIndex);
                this.additionalButtons = allVisibleButtons.slice(splitIndex);
                this.isFull = true;
            }
        });
    }

    /**
     * @param {{ isVisible?: boolean }} slot - slot descriptor from props.slots
     * @returns {boolean} whether the slot should be rendered
     */
    isSlotVisible(slot) {
        return !("isVisible" in slot) || slot.isVisible;
    }
}
